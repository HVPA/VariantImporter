ALTER TABLE hvp_patient MODIFY Ethnicity_id int(11) NULL;
ALTER TABLE hvp_variantinstance MODIFY TestMethod_id int(11) NULL;
ALTER TABLE hvp_variantinstance MODIFY SampleTissue_id int(11) NULL;
ALTER TABLE hvp_variantinstance MODIFY SampleSource_id int(11) NULL;

ALTER TABLE hvp_gene DROP INDEX hvp_gene_SequenceType_id;
ALTER TABLE hvp_gene DROP SequenceType_id;

DROP TABLE hvp_refsequencetype;
