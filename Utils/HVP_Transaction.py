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
# Objectifies the HVP_Transaction xml for manipulation in python
#
################################################################################

import re
import xml.dom.minidom

import logging

from HGVS.Validator import Validator

class XmlObject:
    def __init__(self, tag):
        self.tag = tag
        return
        

def _getSqlInjectionSafeString(str):
    return str.replace("'", "")

def _getOneDomElement(node, tag):
    results = node.getElementsByTagName(tag)
    if len(results) == 0:
        raise Exception("Single tag expected: No %s found" % tag)
    elif len(results) != 1:
        raise Exception("Single tag expected: More than one %s found!" % tag)
    
    return results[0]
    
def _getAtLeastOneDomElement(node, tag):
    results = node.getElementsByTagName(tag)
    if len(results) == 0:
        raise Exception("Tag expected: No %s found" % tag)
    
    return results

def _getTextFromDomElement(node, errorMsg):
    for n in node.childNodes:
        if n.nodeType == n.TEXT_NODE:
            return _getSqlInjectionSafeString(n.nodeValue)
    #raise Exception(errorMsg)
    return None
    
    
def _assertAttrExists(obj, attr):
    if hasattr(obj, attr) == False or getattr(obj, attr) == '' or getattr(obj, attr) is None:
        raise Exception("Missing property: %s" % attr)
def _assertOneOfAttrExists(obj, attrs, errorMsg):
    exists = False
    for attr in attrs:
        if hasattr(obj, attr) and getattr(obj, attr) != '':
            exists = True
    if exists == False:
        raise Exception(errorMsg)
def _assertIntegerIfExists(obj, attr):
    if hasattr(obj, attr) == False:
        return
    str = getattr(obj, attr)
    if str is None or str == '':
        return
    try:
        int(str)
    except ValueError:
        raise Exception("Value not an integer: %s" % attr)
def _assertBoolIfExists(obj, attr):
    if hasattr(obj, attr) == False:
        return
    str = getattr(obj, attr)
    if str is None or str == '':
        return
    if str.lower() in ["true", "false"] == False:
        raise Exception("Value not an boolean: %s" % attr)
def _assertDateIfExists(obj, attr):
    if hasattr(obj, attr) == False:
        return
    str = getattr(obj, attr)
    m = re.match(r'\d\d\d\d-\d\d-\d\d[ -]\d\d:\d\d', str)
    if m == None:
        raise Exception("Value is not a date: %s" % attr)
def _assertValueInListIfExists(obj, attr, list, errorMsg):
    if hasattr(obj, attr) == False:
        return
    str = getattr(obj, attr)
    if str in list == False:
        raise Exception(errorMsg)
        
def _assertHGVS(obj, attr):
    str = getattr(obj, attr)
    if Validator.validate(str) == False:
        raise Exception("Value %s in %s is not a valid HGVS variant" % str, attr)

class GrhaniteHash():
    def __init__(self):
        self.PatientHash = None
        self.Organisation = None
        self.HashType = None
        self.Hash = None
        self.AgrWeight = None
        self.GUID = None
        
class HVP_Transaction(XmlObject):
    def __init__(self):
        self.tag = "HVP_Transaction"
        self.UploadSystem = None
        self.VariantInstances = []
        self.GrhaniteHashes = []
        self.TotalRecords = 0
        
        return
    
    
    def _processUploadSystem(self, node):
        self.UploadSystem = XmlObject(node.tagName)
        self.UploadSystem.Name = node.attributes["name"]
        self.UploadSystem.Version = node.attributes["version"]
    
    def _processVariantInstance(self, node):
        errorMsg = "VariantInstance error: Invalid value node"
        instance = XmlObject(node.tagName)
        for n in node.childNodes:
            if n.nodeType == n.ELEMENT_NODE:
                # Current version of transaction only supports primitives in instance. Error if not
                setattr(instance, n.tagName, _getTextFromDomElement(n, errorMsg))
                
        # Check for mandatory fields
        _assertAttrExists(instance, "OrganisationHashCode")
        _assertAttrExists(instance, "PatientHashCode")
        _assertAttrExists(instance, "GeneName")
        _assertAttrExists(instance, "RefSeqName")
        _assertAttrExists(instance, "RefSeqVer")
        #_assertAttrExists(instance, "Status")
        _assertAttrExists(instance, "VariantHashCode")
        _assertAttrExists(instance, "VariantClass")
        _assertOneOfAttrExists(instance, ["cDNA", "Genomic"], "Missing Variant: Need at least one of cDNA or Genomic")
        #_assertAttrExists(instance, "InstanceDate")
        _assertAttrExists(instance, "Pathogenicity")
        _assertAttrExists(instance, "DateSubmitted")
        
        # Check datatype
        _assertIntegerIfExists(instance, "RefSeqVer")
        #_assertDateIfExists(instance, "InstanceDate")
        _assertIntegerIfExists(instance, "Pathogenicity")
        _assertIntegerIfExists(instance, "PatientAge")
        _assertIntegerIfExists(instance, "TestMethod")
        _assertIntegerIfExists(instance, "SampleTissue")
        #_assertIntegerIfExists(instance, "SampleSource")
        _assertBoolIfExists(instance, "RecordedInDatabase")
        _assertBoolIfExists(instance, "SampleStored")
        _assertBoolIfExists(instance, "PedigreeAvailable")
        _assertBoolIfExists(instance, "VariantSegregatesWithDisease")
        _assertBoolIfExists(instance, "HistologyStored")
        
        
        # Check other rules
        _assertValueInListIfExists(instance, "Status", ["New", "Update", "Delete"], "Invalid value: Status")
        _assertValueInListIfExists(instance, "VariantClass", ["cDNA", "Genomic"], "Invalid value: VariantClass")
        _assertValueInListIfExists(instance, "Gender", ["M", "F", "m", "f", "Male", "Female", "MALE", "FEMALE"], "Invalid value: Gender")
        # TODO: Validate ref values of ref properties
        
        if instance.cDNA != None:
            _assertHGVS(instance, "cDNA")
        if instance.Genomic != None:
            _assertHGVS(instance, "Genomic")
        
        return instance
        
        
    def _processVariantInstances(self, nodes):
        self.TotalRecords = len(nodes)
        for node in nodes:
            try:
                instance = self._processVariantInstance(node)
                self.VariantInstances.append(instance)
                
                # reads the grhanite hashes                
                try:
                    _GrhaniteHashes = _getAtLeastOneDomElement(node, "GrhaniteHash")
                    self._processGrhaniteHashes(_GrhaniteHashes, instance)
                except:
                    # no grhanite hash found, no need to disply error
                    continue
            except Exception, err:
                # Handle this failed instance? Shouldn't need to, stuff should be here clean
                logger = logging.getLogger('hvp')
                logger.error(err)
                continue
    
    def _processGrhaniteHash(self, node):
        errorMsg = "GrhaniteHash error: Invalid value node"
        hash = XmlObject(node.tagName)
        
        for n in node.childNodes:
            if n.nodeType == n.ELEMENT_NODE:
                # Current version of transaction only supports primitives in instance. Error if not
                setattr(hash, n.tagName, _getTextFromDomElement(n, errorMsg))
        
        return hash
    
    # check if hash exists before adding to avoid double up
    def _appendToGrhaniteHashes(hash):
        import pdb; pdb.set_trace()
        hashExist = False
        for h in self.GrhaniteHashes:
            if h.Hash == hash.Hash:
                hashExist = True
                break
        
        if not hashExist:
            self.GrhaniteHashes.append(hash)
                
    
    def _processGrhaniteHashes(self, nodes, instance):
        for node in nodes:
            try:
                grhaniteHash = self._processGrhaniteHash(node)
                
                hash = GrhaniteHash()
                hash.PatientHash = instance.PatientHashCode
                hash.Organisation = instance.OrganisationHashCode
                hash.HashType = grhaniteHash.HashType
                hash.Hash = grhaniteHash.Hash
                hash.AgrWeight = grhaniteHash.AgrWeight
                hash.GUID = grhaniteHash.GUID
                
                #_appendToGrhaniteHashes(hash)
                hashExist = False
                for h in self.GrhaniteHashes:
                    if h.Hash == hash.Hash:
                        hashExist = True
                        break
                
                if not hashExist:
                    self.GrhaniteHashes.append(hash)
                
            except Exception, err:
                logger = logging.getLogger('hvp')
                logger.error(err)
                continue
    
    
    def parse(self, filename):
        dom = xml.dom.minidom.parse(filename)
        
        root = _getOneDomElement(dom, "HVP_Transaction")
        self.Version = root.attributes["version"]
        self.DateCreated = root.attributes["dateCreated"]
        self.Destination = root.attributes["destination"]

        _UploadSystem = _getOneDomElement(root, "UploadSystem")
        self._processUploadSystem(_UploadSystem)
        
        _VariantInstances = _getAtLeastOneDomElement(root, "VariantInstance")
        self._processVariantInstances(_VariantInstances)
        

        
        
