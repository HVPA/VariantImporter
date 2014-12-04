################################################################################
# 
# Human Variome Database Portal.
#
# === License ===
#
# Last Author:   $Author: MelvinLuong $
# Last Revision: $Rev: 247 $
# Last Modified: $Date: 2011-02-09 13:22:40 +1100 (Wed, 09 Feb 2011) $ 
#
# === Description ===
# Manages the writing of data in the HVP node.
# CommandLine pattern style, where by the Import program mearly drives the
# import utility using this to perform the operations
#
################################################################################


import MySQLdb
#import datetime
#import settings
#import variant_parser
#from dateutil.parser import *
import os.path
import logging

from Bio.Blast import NCBIXML

from HGVS.Parser import Parser

# Returns a value that is suitable for an SQL value
def _sqlvalue(instance, prop):
    val = None
    if hasattr(instance, prop):
        val = getattr(instance, prop)
    if val is None:
        return 'NULL'
    return "'%s'" % str(val)
    
        
# A connection that may remain open all the time until closed
class ManagedConnection:

    def __init__(self, hostname, username, password, database):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.database = database
        
        self.conn = None

    def _createConnection(self):
        return MySQLdb.connect(self.hostname, self.username, self.password, self.database)
        
        
    def get(self):
        if self.conn == None:
            self.conn = self._createConnection()
        elif self.conn.open != 1:
            self.conn = self._createConnection()
        
        return self.conn
       
    def close(self):
        if self.conn != None and self.conn.open == 1:
            self.conn.close()
            self.conn = None

class HVP_DataManager:
    def _buildLookup(self, lookupName, tableName, valName, idName):
        self.lookups[lookupName] = {}
        self.lookupValues[lookupName] = (tableName, valName, idName)
    
    def _fillLookup(self, lookupName, tableName, valName, idName):
        conn = self.managedConnection.get()
        cursor = conn.cursor()
        cursor.execute("SELECT %s, %s FROM %s" % (idName, valName, tableName))
        result = cursor.fetchall()
    
        lookup = {}
        
        for row in result:
            lookup[row[1]] = row[0]
            
        self.lookups[lookupName] = lookup
        
    def _buildAndFillLookup(self, lookupName, tableName, valName, idName):
        self._buildLookup(lookupName, tableName, valName, idName)
        self._fillLookup(lookupName, tableName, valName, idName)


    def _lookup(self, name, val):
        if self.lookups.has_key(name) == False:
            raise Exception("Lookup %s not apart of import routine" % name)
        
        if self.lookups[name].has_key(val) == False:
            conn = self.managedConnection.get()
            cursor = conn.cursor()
            tableName = self.lookupValues[name][0]
            valName = self.lookupValues[name][1]
            idName = self.lookupValues[name][2]
            cursor.execute("SELECT %s FROM %s WHERE %s = '%s'" % (idName, tableName, valName, val))
            
            result = cursor.fetchone()
            if result is None:
                raise Exception("Value '%s' is not apart of %s" % (val, tableName))
                
            self.lookups[name][val] = result[0]
            
        return str(self.lookups[name][val])
    
    # Does a look up only if propName in instance is exists
    # returns None if not there
    def _optionalLookup(self, name, instance, propName):
        if hasattr(instance, propName) and not getattr(instance, propName) is None:
            return str(self._lookup(name, getattr(instance, propName)))
            
        return 'NULL'
   
    # Does a lookup on samplesource, if match found returns the ID
    def _doRefSampleSourceLookup(self, sampleSource):    
        conn = self.managedConnection.get()
        cursor = conn.cursor()
        cursor.execute("SELECT ID FROM hvp_refsamplesource WHERE LOWER(SampleSource) = LOWER('%s')" % (sampleSource))
        result = cursor.fetchone()

        if result is None:
            return 'NULL'
        else:
            return result[0]

    
    # Special lookup for gene, get the gene based GeneName and RefSeqName
    # Records the refseq name and version 
    def _doGeneLookup(self, geneName, refSeqName, refSeqVer):
        # Not in lookup so, ask the database for it
        conn = self.managedConnection.get()
        cursor = conn.cursor()
        cursor.execute("SELECT id, RefSeqName, RefSeqVer, GenBankName, GenBankVer FROM hvp_gene WHERE GeneName = '%s' and RefSeqName = '%s' and RefSeqVer = '%s'" % (geneName, refSeqName, refSeqVer))
        result = cursor.fetchone()
    
        if result is None:
            #raise Exception("Gene not on the node!")
            self.logger.info("Error: Gene " + geneName + refSeqName + '.' + refSeqVer + " not found on HVP database")
            return None
        else:
            self.geneLookup[geneName] = (result[0], result[1], result[2], result[3], result[4])
        return result[0]

    # Special case lookup
    # Search by geneId, but also cDNA or genomic depending on variant class
    # If it isnt there, add it!
    # beenHere is a just-in-case for recursion to avoid infinite loop
    def _doVariantLookup(self, variantClassId, cDNA, genomic, protein, mRNA, geneId, beenHere = False):
        value = None
        colName = None
        if variantClassId == '1': # Genomic
            value = genomic
            colName = "Genomic"
        elif variantClassId == '2': # Mitochrondrial/cDNA
            value = cDNA
            colName = "cDNA"
        
        if value is None:
            raise Exception("Variant Class Id: %s is unknown" % variantClassId)
            
        # check lookup first
        if self.variantLookup.has_key((geneId, variantClassId, value)):
            return self.variantLookup[(geneId, variantClassId, value)] # just return it since its there!
            
        conn = self.managedConnection.get()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM hvp_variant WHERE Gene_ID = %s AND VariantClass_id = %s AND %s = '%s'" % (geneId, variantClassId, colName, value))
        result = cursor.fetchone()

        if result is None:
            if beenHere == True:
                self.logger.inf("Variant Class: Been here!")
                return
        
            # Insert, then call this func again to return the result
            try:
                cursor.execute("INSERT INTO hvp_variant (Gene_id, cDNA, Genomic, Protein, mRNA, VariantClass_id) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % (geneId, cDNA, genomic, protein, mRNA, variantClassId))
                return self._doVariantLookup(variantClassId, cDNA, genomic, protein, mRNA, geneId, True)
            except:
                conn.rollback()
                return None
        
        
        self.variantLookup[(geneId, variantClassId, value)] = result[0]
        return result[0]
        
    # Special case for patient lookup
    # If not there, add and return it too
    def _doPatientLookup(self, hashCode, beenHere = False):
        # Try lookup cache first
        if self.patientLookup.has_key(hashCode):
            return self.patientLookup[hashCode]
                  
        # Not there! so search
        conn = self.managedConnection.get()
        cursor = conn.cursor()
        cursor.execute("SELECT HashCode FROM hvp_patient WHERE HashCode = '%s'" % (hashCode))
        result = cursor.fetchone()
        
        if result is None:
            if beenHere == True:
                #raise Exception("Patient been here!")
                self.logger.info("Patient been here!")
                return
            
            # insert and call again
            try:
                cursor.execute("INSERT INTO hvp_patient (HashCode) VALUES ('%s')" % (hashCode))
                return self._doPatientLookup(hashCode, True)
            except:
                conn.rollback()
            
        self.patientLookup[hashCode] = result[0] # both hash and result should be the same anyway
        
        return result[0]
    
    
    def __init__(self, logger, hostname, username, password, database):
        self.logger = logger
        self.managedConnection = ManagedConnection(hostname, username, password, database)
        
        self.lookups = {}
        self.lookupValues = {}
        
        self.geneLookup = {}
        self.variantLookup = {}
        self.patientLookup = {}
        
        self._buildAndFillLookup("VariantClass", "hvp_refvariantclass", "id", "id")
        self._buildAndFillLookup("Pathogenicity", "hvp_refpathogenicity", "id", "id")
        self._buildAndFillLookup("SampleTissue", "hvp_refsampletissue", "id", "id")
        self._buildAndFillLookup("SampleSource", "hvp_refsamplesource", "id", "id")
        self._buildAndFillLookup("TestMethod", "hvp_reftestmethod", "id", "id")
        self._buildAndFillLookup("Organisation", "hvp_organisation", "HashCode", "HashCode")
        
        
        
        self.managedConnection.close()
        

    # Internal function. Returns the right cDNA given the refseq compared to node
    # Simple implementation - only checks for the alignment offset (applies to BRCA1)
    # Will need to compare on a gene/ver-by-gene/ver basis
    def _convertCDNA(self, diff_dir, gene, cDNA, refSeqName, refSeqVer):
        if gene[1] == refSeqName and gene[2] == refSeqVer: # Should only really differ by version number
            return cDNA
        else:
            diff_name = os.path.join(diff_dir, "%s.%sto%s.xml" % (gene[1], refSeqVer, gene[2]))
            if not(os.path.isfile(diff_name)):
                raise Exception("No BLAST xml diff file for %s from %s to %s" % (gene[1], refSeqVer, gene[2]))
            f = open(diff_name)
            blast_records = list(NCBIXML.parse(f))
            f.close()

            if len(blast_records) < 1:
                raise Exception("BLAST xml diff does not have at least one record")
            if len(blast_records[0].alignments) < 1:
                raise Exception("BLAST xml diff does not have at least one alignment")
            if len(blast_records[0].alignments[0].hsps) < 1:
                raise Exception("BLAST xml diff does not have at least one hsps in alignment")

            hsp = blast_records[0].alignments[0].hsps[0]
            offset = hsp.sbjct_start - 1

            parser = Parser()
            variant =  parser.parse("", cDNA)

            if variant.position != '' and variant.position.find('*') < 0:
                variant.position = str(int(variant.position) + offset)
            if variant.range_lower != '' and variant.range_lower.find('*') < 0:
                variant.range_lower = str(int(variant.range_lower) + offset)
            if variant.range_upper != '' and variant.range_upper.find('*') < 0:
                variant.range_upper = str(int(variant_range_upper) + offset)
      
            cDNA = variant.ToString()
            
            return cDNA


    # instance lookup
    def _doVariantInstanceLookup(self, instanceHash):
        conn = self.managedConnection.get()
        cursor = conn.cursor()
        cursor.execute("SELECT HashCode FROM hvp_variantinstance where HashCode = '%s'" % (instanceHash))
        result = cursor.fetchone()
        
        if result is None:
            return False
        else:
            return True

    # Check if grhanite hash already exist in db
    def _doGrhaniteLookup(self, grhaniteHash):
        # search in db
        conn = self.managedConnection.get()
        cursor = conn.cursor()
        cursor.execute("SELECT Hash FROM hvp_grhanitehash where Hash = '%s'" % (grhaniteHash))
        result = cursor.fetchone()
        
        return result
    
    def processTransaction(self, transaction, diff_dir):
        logger = self.logger # shorthand
        logger.info("Processing...")
        failed_import = False
        # saves variant instances
        for instance in transaction.VariantInstances:
            #if instance.Status == "New":
                # check instance Hash if it already exist in hvp db
                if not self._doVariantInstanceLookup(instance.VariantHashCode):
                    variantClassId = self._lookup("VariantClass", instance.VariantClass)
                    geneId = self._doGeneLookup(instance.GeneName, instance.RefSeqName, instance.RefSeqVer)
                    
                    # skip if no matching gene found
                    if geneId == None:
                        failed_import = True
                    else:
                        # If we got here, gene has been found and loaded in lookup
                        gene = self.geneLookup[instance.GeneName]

                        # Check if cDNA needs conversion
                        #if not instance.cDNA is None:
                        #    instance.cDNA = self._convertCDNA(diff_dir, gene, instance.cDNA, instance.RefSeqName, instance.RefSeqVer)
               
                        # TODO: 
                        # Check if Genome needs conversion
                        ##if not(gene[3] == instance.GeneBankName and gene[4] == instance.GeneBankVer):
                        ###convert
                
                        HashCode = _sqlvalue(instance, "VariantHashCode")
                        Variant_id = self._doVariantLookup(variantClassId, instance.cDNA, instance.Genomic, instance.Protein, instance.mRNA, geneId)
                        InstanceDate = _sqlvalue(instance, "InstanceDate")
                        PatientAge = _sqlvalue(instance, "PatientAge")
                        TestMethod_id = self._optionalLookup("TestMethod", instance, "TestMethod")
                        SampleTissue_id = self._optionalLookup("SampleTissue", instance, "SampleTissue")
                        #SampleSource_id = self._optionalLookup("SampleSource", instance, "SampleSource")
                        SampleSource_id = self._doRefSampleSourceLookup(instance.SampleSource)
                        Pathogenicity_id = self._lookup("Pathogenicity", instance.Pathogenicity)
                        Justification = _sqlvalue(instance, "Justification")
                        PubMed = _sqlvalue(instance, "PubMed")
                        RecordedInDatabase = _sqlvalue(instance, "RecordedInDatabase")
                        SampleStored = _sqlvalue(instance, "SampleStored")
                        PedigreeAvailable = _sqlvalue(instance, "PedigreeAvailable")
                        VariantSegregatesWithDisease = _sqlvalue(instance, "VariantSegregatesWithDisease")
                        HistologyStored = _sqlvalue(instance, "HistologyStored")
                        Patient_id = "'%s'" % self._doPatientLookup(instance.PatientHashCode)
                        Organisation_id = "'%s'" % self._lookup("Organisation", instance.OrganisationHashCode)
                        DateSubmitted = _sqlvalue(instance, "DateSubmitted")

                
                        conn = self.managedConnection.get()
                        cursor = conn.cursor()
                        insertQuery = "\
        INSERT INTO hvp_variantinstance \
        (HashCode, Variant_id, InstanceDate, PatientAge, TestMethod_id, SampleTissue_id, SampleSource_id, \
        Pathogenicity_id, Justification, PubMed, RecordedInDatabase, SampleStored, PedigreeAvailable, \
        VariantSegregatesWithDisease, HistologyStored, Patient_id, Organisation_id, DateSubmitted) \
        VALUES \
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);" % (HashCode, Variant_id, InstanceDate, PatientAge, TestMethod_id, SampleTissue_id, SampleSource_id, Pathogenicity_id, Justification, PubMed, RecordedInDatabase, SampleStored, PedigreeAvailable, VariantSegregatesWithDisease, HistologyStored, Patient_id, Organisation_id, DateSubmitted)
                        #print insertQuery
                        cursor.execute(insertQuery)

                        # TODO: Update
                        # TODO: Delete
            
                        # save grhanite hash data
                        for hash in transaction.GrhaniteHashes:
                            # check if grhanite hash exist
                            if self._doGrhaniteLookup(hash.Hash) is None:
                                # insert if result return None        
                                conn = self.managedConnection.get()
                                cursor = conn.cursor()
                                cursor.execute('''
                                    INSERT INTO hvp_grhanitehash (HashType, Hash, AgrWeight, Grhanite_GUID, Site_id, PatientHash_id) 
                                    VALUES ('%s', '%s', '%s', '%s', '%s', '%s');
                                    ''' % (hash.HashType, hash.Hash, hash.AgrWeight, hash.GUID, hash.Organisation, hash.PatientHash))
            
        logger.info("Processing complete!")
        return failed_import
