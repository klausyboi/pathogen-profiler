import pathogenprofiler as pp
import json
import argparse



def main(args):
	if pp.nofolder(args.out_dir):
		pp.run_cmd("mkdir %s" % args.out_dir)
	conf = {
		"ref":args.ref,
		"gff":args.gff,
		"bed":args.bed,
		"ann":args.ann,
		}
	if args.conf:
		conf = json.load(open(args.conf))
	print(conf)
	for x in ["ref","gff","bed","ann"]:
		if conf[x]==None:
			pp.log("%s variable is not defined" % x,True)
	bam_obj = pp.bam(
		args.bam,
		args.prefix,
		conf["ref"],
		platform=args.platform
	)
	bcf_obj = bam_obj.call_variants(
		prefix=args.prefix+".targets",
		call_method=args.call_method,
		gff_file=conf["gff"],
		bed_file=conf["bed"],
		mixed_as_missing=False if args.platform == "Illumina" else True,
		threads=args.threads,
		min_dp=args.min_depth,
		af=args.af
	)
	csq = bcf_obj.load_csq(ann_file=conf["ann"])
	variants = list(csq.values())[0]
	if args.delly:
		delly_bcf = bam_obj.run_delly()
		deletions = delly_bcf.overlap_bed(conf["bed"])
		for deletion in deletions:
			tmp = {"genome_pos":deletion["start"],"gene_id":deletion["region"],"chr":deletion["chr"],"freq":1,"type":"large_deletion","change":"%(chr)s_%(start)s_%(end)s" % deletion}
			variants.append(tmp)
	json.dump(variants,open("%s/%s.pp-results.json" % (args.out_dir,args.prefix),"w"))


parser = argparse.ArgumentParser(description='get mutations pipeline',formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('bam', help='Fasta file')
parser.add_argument('prefix', help='Fasta file')
parser.add_argument('--conf', help='Fasta file')
parser.add_argument('--ref', help='Fasta file')
parser.add_argument('--gff', help='Fasta file')
parser.add_argument('--bed', help='Fasta file')
parser.add_argument('--ann', help='Fasta file')
parser.add_argument('--delly',action="store_true", help='Fasta file')
parser.add_argument('--call-method',default="low", help='Fasta file')
parser.add_argument('--platform',default="Illumina", help='Fasta file')
parser.add_argument('--threads',default=1, help='Fasta file')
parser.add_argument('--min-depth',default=10, help='Fasta file')
parser.add_argument('--af',default=0.1, help='Fasta file')
parser.add_argument('--out-dir',default="pp-results", help='Fasta file')
parser.set_defaults(func=main)

args = parser.parse_args()
args.func(args)
