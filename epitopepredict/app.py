#!/usr/bin/env python

"""
    MHC prediction command line script
    Created March 2016
    Copyright (C) Damien Farrell
"""

from __future__ import absolute_import, print_function
import sys, os
import shutil
import pandas as pd
from collections import OrderedDict
from . import base, config, analysis, sequtils, plotting, tests

defaultpath = os.getcwd()

def get_sequences(filename):
    """Determine file type and get sequences"""

    ext = os.path.splitext(filename)[1]
    if ext in ['.fa','.faa','.fasta']:
        seqs = sequtils.fasta_to_dataframe(filename)
        print ('found fasta file')
    elif ext in ['.gb','.gbk','.genbank']:
        seqs = sequtils.genbank_to_dataframe(filename, cds=True)
        print ('found genbank file')
    return seqs

def run(predictors=[], cutoff=0.98, cutoff_method='default',
         mhc2_alleles='', mhc1_alleles='',
         mhc1_length=11, mhc2_length=15,
         iedb_mhc1_method='IEDB_recommended',
         iedb_mhc2_method='IEDB_recommended',
         n=2,  sequence_file='',
         path='',
         overwrite=False,
         verbose=False,
         plots=False,
         genome_analysis=False,
         names = '', **kwargs):
    """Run the prediction workflow using config settings"""

    sequences = get_sequences(sequence_file)
    #print (sequences)
    mhc1_alleles = mhc1_alleles.split(',')
    mhc2_alleles = mhc2_alleles.split(',')
    predictors = predictors.split(',')
    if mhc1_alleles[0] in base.mhc1_presets:
        mhc1_alleles = base.get_preset_alleles(mhc1_alleles[0])
    elif mhc2_alleles[0] in base.mhc2_presets:
        mhc2_alleles = base.get_preset_alleles(mhc2_alleles[0])

    cutoff = float(cutoff)
    names = names.split(',')
    if names == ['']: names=None

    if not os.path.exists(path) and path != '':
        os.mkdir(path)
    preds = []
    for p in predictors:
        print ('predictor:', p)
        P = base.get_predictor(p)
        preds.append(P)
        savepath = os.path.join(path, p)
        if overwrite == True and os.path.exists(savepath):
            shutil.rmtree(savepath)
        if p in ['iedbmhc1','mhcflurry']:
            a = mhc1_alleles
            length = mhc1_length
            check_mhc1_length(length)
            method = iedb_mhc1_method
        else:
            a = mhc2_alleles
            length = mhc2_length
            method = iedb_mhc2_method
        print ('alleles:',a)
        if p == 'iedbmhc1' and check_iedbmhc1_path() == False:
            continue

        P.predictProteins(sequences, length=length, alleles=a, names=names,
                          path=savepath, overwrite=overwrite, verbose=verbose,
                          method=method)
        #load into predictor
        P.load(path=savepath)
        if P.data is None:
            print ('no results were found, did predictor run?')
            return
        b = P.getBinders(cutoff=cutoff)#, value=cutoff_method)
        b.to_csv(os.path.join(path,'binders_%s_%s.csv' %(p,n)))

        pb = P.promiscuousBinders(n=int(n), cutoff=cutoff)
        print ('found %s promiscuous binders at cutoff %s' %(len(pb),cutoff))
        pb.to_csv(os.path.join(path,'prom_binders_%s_%s.csv' %(p,n)))
        if verbose == True:
            print ('top promiscuous binders:')
            print (pb[:10])
        if genome_analysis == True:
            cl = analysis.find_clusters(pb, genome=sequences)
            cl.to_csv(os.path.join(path,'clusters_%s.csv' %p))
        print ('-----------------------------')

    #various choices here - we could generate a notebook with the plots
    #embedded ? better than saving all to disk
    prots = sequences.locus_tag
    if plots == True:
        import pylab as plt
        height = 2*len(preds)
        for prot in prots:
            ax = plotting.plot_tracks(preds,name=prot,n=2,cutoff=cutoff,
                                          figsize=(14,height),legend=True)
            #plotting.mpl_plot_regions(coords, ax, color='gray')
            plt.tight_layout()
            plt.savefig('plots/%s.png'%prot, dpi=150)
        print ('saved plots')

    return

def check_mhc1_length(l):
    if l<9 or l>13:
        print ('use MHCI n-mer lengths from 9-13')
        return False

def check_iedbmhc1_path():
    if not os.path.exists(base.iedbmhc1path):
        print ('IEDB MHC tools not found, check path')
        return False

def show_preset_alleles():
    print ('preset allele list ids:')
    for i in base.mhc1_presets+base.mhc2_presets:
        print (i, len( base.get_preset_alleles(i)))

def print_help():
    print ("""use -h to get options""")

def main():
    "Run the application"

    import sys, os
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-c", "--config", dest="config",
                        help="Configuration file", metavar="FILE")
    parser.add_option("-r", "--run", dest="run",  action="store_true",
                        default=False, help="Run the predictions")
    parser.add_option("-p", "--presets", dest="presets",  action="store_true",
                        default=False, help="Show preset allele lists")
    parser.add_option("-l", "--list-alleles", dest="list-alleles",  action="store_true",
                        default=False, help="List available alleles")
    parser.add_option("-t", "--test", dest="test",  action="store_true",
                        default=False, help="Do quick test")
    opts, remainder = parser.parse_args()
    if opts.config != None:
        cp = config.parse_config(opts.config)
        options = config.get_options(cp)
        options = config.check_options(options)
    else:
        conffile = 'default.conf'
        if not os.path.exists(conffile):
            config.write_default_config(conffile, defaults=config.baseoptions)
    if opts.presets == True:
        show_preset_alleles()
    elif opts.run == True:
        base.iedbmhc1path = options['iedbmhc1_path']
        base.iedbmhc2path = options['iedbmhc2_path']
        run(**options)
    else:
        print_help()

if __name__ == '__main__':
    main()
