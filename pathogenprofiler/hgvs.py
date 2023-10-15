import re
import logging
from .utils import cmd_out, Gene, revcom
from typing import Tuple, List
from pysam import FastaFile
from uuid import uuid4
import os


supported_so_terms = [
    'coding_sequence_variant', 'chromosome', 'duplication', 'inversion', 'coding_sequence_variant', 
    'inframe_insertion', 'disruptive_inframe_insertion', 'inframe_deletion', 'disruptive_inframe_deletion', 
    'downstream_gene_variant', 'exon_variant', 'exon_loss_variant', 'exon_loss_variant', 'duplication', 
    'duplication', 'inversion', 'inversion', 'frameshift_variant', 'gene_variant', 'feature_ablation', 
    'duplication', 'gene_fusion', 'gene_fusion', 'bidirectional_gene_fusion', 'rearranged_at_DNA_level', 
    'intergenic_region', 'conserved_intergenic_variant', 'intragenic_variant', 'intron_variant', 
    'conserved_intron_variant', 'miRNA', 'missense_variant', 'initiator_codon_variant', 'stop_retained_variant', 
    'protein_protein_contact', 'structural_interaction_variant', 'rare_amino_acid_variant', 
    'splice_acceptor_variant', 'splice_donor_variant', 'splice_region_variant', 'splice_region_variant', 
    'splice_region_variant', 'stop_lost', '5_prime_UTR_premature_', 'start_codon_gain_variant', 
    'start_lost', 'stop_gained', 'synonymous_variant', 'start_retained', 'stop_retained_variant', 
    'transcript_variant', 'transcript_ablation', 'regulatory_region_variant', 'upstream_gene_variant', 
    '3_prime_UTR_variant', '3_prime_UTR_truncation + exon_loss', '5_prime_UTR_variant', 
    '5_prime_UTR_truncation + exon_loss_variant', 'sequence_feature + exon_loss_variant', 'functionally_normal'
]

def get_genome_coords(pos: int,gene: Gene) -> int:
    """
    Convert a position in a gene to a position in the genome.
    
    Parameters:
    pos (int): The position in the gene.
    gene (Gene): The gene in which the position occurs.
    
    Returns:
    int: The position in the genome.
    """
    if gene.strand=="+":
        genome_pos = gene.start + pos - 1
        if pos<0:
            genome_pos+=1
    if gene.strand=="-":
        genome_pos = gene.start - pos + 1
        if pos<0:
            genome_pos-=1
    return genome_pos

def extract_insertion(hgvs: str, gene: Gene) -> str:
    """
    Extract the insertion sequence from an HGVS insertion mutation.
    
    Parameters:
    hgvs (str): The HGVS insertion mutation.
    gene (Gene): The gene in which the mutation occurs.
    
    Returns:
    str: The insertion sequence.
    """
    r = re.search(r"ins([ACTG]+)", hgvs)
    insertion = r.group(1)
    if gene.strand=="-":
        insertion = revcom(insertion)
    return insertion

def extract_duplication(hgvs: str, gene: Gene) -> str:
    """
    Extract the duplication sequence from an HGVS duplication mutation.
    
    Parameters:
    hgvs (str): The HGVS duplication mutation.
    gene (Gene): The gene in which the mutation occurs.
    
    Returns:
    str: The duplication sequence.
    """
    r = re.search(r"dup([ACTG]+)", hgvs)
    duplication = r.group(1)
    if gene.strand=="-":
        duplication = revcom(duplication)
    return duplication

def extract_numbers(s: str) -> List[int]:
    """
    Extract all the numbers from a string.
    
    Parameters:
    s (str): The input string from which to extract numbers.
    
    Returns:
    List[int]: A list of integers extracted from the input string.
    """
    # Find all numeric substrings using a regex
    numbers_str = re.findall(r'-?\d+', s)
    
    # Convert the numeric substrings to integers and return them
    return [int(num_str) for num_str in numbers_str]

def parse_coding_indel(mutation: str, gene: Gene, ref_object: FastaFile) -> dict:
    """
    Parse an indel mutation in HGVS format and return a dictionary of VCF components.
    
    Parameters:
    mutation (str): The indel mutation in HGVS format.
    gene (Gene): The gene in which the mutation occurs.

    Returns:
    dict: A dictionary of VCF components.
    """     
    numbers = extract_numbers(mutation)  
    if len(numbers)==2:
        start,end = numbers
    else:
        start = numbers[0]
        end = start
    start = get_genome_coords(start,gene)
    end = get_genome_coords(end,gene)
    if start>end:
        start,end = end,start
    if "del" in mutation:
        vcf_pos = start - 1
        ref = ref_object.fetch(gene.chrom,vcf_pos-1,end)
        alt = ref[0]
    if "ins" in mutation:
        if "del" not in mutation:
            vcf_pos = start
            ref = ref_object.fetch(gene.chrom,vcf_pos-1,end-1)
        alt = ref[0] + extract_insertion(mutation,gene)
    return {"chrom":gene.chrom,"pos":vcf_pos, "ref":ref, "alt":alt,"gene":gene.locus_tag,"type":"nucleotide"}

def parse_snv(mutation: str, gene: Gene, ref_object: FastaFile) -> dict:
    """
    Parse a SNV mutation in HGVS format and return a dictionary of VCF components.
    
    Parameters:
    mutation (str): The SNV mutation in HGVS format.
    gene (Gene): The gene in which the mutation occurs.

    Returns:
    dict: A dictionary of VCF components.
    """ 
    numbers = extract_numbers(mutation)
    vcf_pos = get_genome_coords(numbers[0],gene)
    ref = ref_object.fetch(gene.chrom,vcf_pos-1,vcf_pos)
    alt = mutation[-1]
    if gene.strand=="-":
        alt = revcom(alt)
    return {"chrom":gene.chrom,"pos":vcf_pos, "ref":ref, "alt":alt,"gene":gene.locus_tag,"type":"nucleotide"}

def parse_genomic_snv(mutation: str,gene: Gene,ref_object: FastaFile) -> dict:
    """
    Parse a SNV mutation in HGVS format and return a dictionary of VCF components.
    
    Parameters:
    mutation (str): The SNV mutation in HGVS format.
    gene (Gene): The gene in which the mutation occurs.
    ref_object (FastaFile): The reference genome.

    Returns:
    dict: A dictionary of VCF components.
    """ 
    r = re.search("g.([0-9]+)([ACGT])>([ACGT])",mutation)
    vcf_pos = int(r.group(1))
    ref = r.group(2)
    alt = r.group(3)
    return {"chrom":gene.chrom,"pos":vcf_pos, "ref":ref, "alt":alt,"gene":gene.locus_tag,"type":"nucleotide"}


def parse_duplication(mutation: str, gene: Gene, ref_object: FastaFile) -> dict:
    """
    Parse a duplication mutation in HGVS format and return a dictionary of VCF components.
    
    Parameters:
    mutation (str): The duplication mutation in HGVS format.
    gene (Gene): The gene in which the mutation occurs.

    Returns:
    dict: A dictionary of VCF components.
    """ 
    numbers = extract_numbers(mutation)
    genome_positions = [get_genome_coords(p,gene) for p in numbers]
    vcf_pos = min(genome_positions) - 1

    ref = ref_object.fetch(gene.chrom,vcf_pos-1,vcf_pos)
    alt = ref + extract_duplication(mutation,gene)
    return {"chrom":gene.chrom,"pos":vcf_pos, "ref":ref, "alt":alt,"gene":gene.locus_tag,"type":"nucleotide"}


def get_ann(variants,snpEffDB):
    uuid = str(uuid4()) #"463545ef-71fc-449b-8f4e-9c907ee6fbf5"
    with open(uuid,"w") as O:
        O.write('##fileformat=VCFv4.2\n')
        O.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n')
        O.write('#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\ttest\n')
        for var in variants.values():
            O.write("%(chrom)s\t%(pos)s\t.\t%(ref)s\t%(alt)s\t255\t.\t.\tGT\t1\n" % var) 
    results = {}
    keys = list(variants.keys())
    vals = list(variants.values())
    i = 0
    for l in cmd_out(f"snpEff ann {snpEffDB} {uuid}"):
        if l[0]=="#": continue
        row = l.strip().split()
        for ann in row[7].split(","):
            a = ann.split("|")
            if len(a)!=16:continue

            if vals[i]["gene"] in [a[3],a[4]]:
                results[keys[i]] = a[9] if vals[i]["type"]=="nucleotide" else a[10]
        i+=1
    os.remove(uuid)
    return results


def verify_mutation_list(hgvs_mutations: List[dict], genes: List[Gene], refseq: FastaFile, snpEffDB: str) -> dict:
    """
    Break down a list of mutations info a list of VCF components and use SNPeff to reconvert to hgvs.

    Parameters:
    mutations (List[dict]): A list of mutations.
    genes (List[Gene]): A list of genes.
    refseq (FastaFile): The reference genome.

    Returns:
    dict: A dictionary of the original mutation and the recoded hgvs.
    """

    converted_mutations = {}
    mutations_genome = {}
    for row in hgvs_mutations:
        logging.debug(row)
        gene = [g for g in genes if g.name==row["Gene"] or g.locus_tag==row["Gene"]][0]

        # Protein variants - not validated yet
        if r := re.search("p\..+",row["Mutation"]):
            converted_mutations[(row["Gene"],row["Mutation"])] = row["Mutation"]

        # Coding indels
        elif "del" in row["Mutation"] or "ins" in row["Mutation"]:
            logging.debug("asjdapisdjasiopdjasoidjaosijdoai**************")
            mutations_genome[(row["Gene"],row["Mutation"])] = parse_coding_indel(row["Mutation"],gene,refseq)

        # Duplication
        elif "dup" in row["Mutation"]:
            mutations_genome[(row["Gene"],row["Mutation"])] = parse_duplication(row["Mutation"],gene,refseq)

        # Coding SNPs
        elif re.search("c.(-?[0-9]+)([ACGT])>([ACGT])",row["Mutation"]):
            mutations_genome[(row["Gene"],row["Mutation"])] = parse_snv(row["Mutation"],gene,refseq)

        # Genomic SNPs
        elif re.search("g.([0-9]+)([ACGT])>([ACGT])",row["Mutation"]):
            mutations_genome[(row["Gene"],row["Mutation"])] = parse_genomic_snv(row["Mutation"],gene,refseq)

        # Non-coding SNPs
        elif re.search("n.(-?[0-9]+)([ACGT]+)>([ACGT]+)",row["Mutation"]):
            mutations_genome[(row["Gene"],row["Mutation"])] = parse_snv(row["Mutation"],gene,refseq)

        elif row['Mutation'] in supported_so_terms:
            converted_mutations[(row["Gene"],row['Mutation'])] = row['Mutation']

    logging.debug(mutations_genome)
    if len(mutations_genome)>0:
        mutation_conversion = get_ann(mutations_genome,snpEffDB)
        for key in mutation_conversion:
            converted_mutations[key] = mutation_conversion[key]
    
    logging.debug(converted_mutations)
    return converted_mutations