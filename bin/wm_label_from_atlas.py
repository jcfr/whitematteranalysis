import numpy
import argparse
import os
import multiprocessing
import vtk

try:
    import whitematteranalysis as wma
except:
    print "<wm_label_from_atlas.py> Error importing white matter analysis package\n"
    raise

HAVE_PLT = 1
try:
    import matplotlib.pyplot as plt
except:
    print "<wm_label_from_atlas.py> Error importing matplotlib.pyplot package, can't plot quality control data.\n"
    HAVE_PLT = 0    

#-----------------
# Parse arguments
#-----------------
parser = argparse.ArgumentParser(
    description="Runs clustering of tractography for multiple subjects to create an atlas.",
    epilog="Written by Lauren O\'Donnell, odonnell@bwh.harvard.edu.  Please reference \"O'Donnell, Lauren J., and C-F. Westin. Automatic tractography segmentation using a high-dimensional white matter atlas. Medical Imaging, IEEE Transactions on 26.11 (2007): 1562-1575.\"")
parser.add_argument("-v", "--version",
    action="version", default=argparse.SUPPRESS,
    version='1.0',
    help="Show program's version number and exit")
parser.add_argument(
    'inputFile',
    help='A file of whole-brain tractography as vtkPolyData (.vtk or .vtp).')
parser.add_argument(
    'atlasDirectory',
    help='The directory where the atlas is stored. Must contain atlas.p and atlas.vtp')
parser.add_argument(
    'outputDirectory',
    help='The output directory will be created if it does not exist.')
parser.add_argument(
    '-f', action="store", dest="numberOfFibers", type=int,
    help='Number of fibers to analyze from each subject.')
parser.add_argument(
    '-l', action="store", dest="fiberLength", type=int,
    help='Minimum length (in mm) of fibers to analyze. 25mm is default.')
parser.add_argument(
    '-j', action="store", dest="numberOfJobs", type=int,
    help='Number of processors to use.')
parser.add_argument(
    '-verbose', action='store_true', dest="flag_verbose",
    help='Verbose. Run with -verbose for more text output.')
parser.add_argument(
    '-k', action="store", dest="numberOfClusters", type=int,
    help='Number of clusters to find. Default is 200. Useful range is from 200 to 500+.')
parser.add_argument(
    '-thresh', action="store", dest="distanceThreshold", type=float,
    help='Threshold (in mm) below which fiber points are considered in the same position. 0mm is default. Set to 2mm for cross-subject clustering.')
parser.add_argument(
    '-nystrom_sample', action="store", dest="sizeOfNystromSample", type=int,
    help='Number of fibers to use in the Nystrom sample. 2000 is default. Must be >1500. Increase for larger datasets. Reduce to limit memory use.')
parser.add_argument(
    '-sigma', action="store", dest="sigma", type=float,
    help='Sigma for kernel. Controls distance over which fibers are considered similar. 60mm is default. Reduce for stricter clustering with ample data, or for physically smaller problems like a subset of the brain.')
parser.add_argument(
    '-mrml_fibers', action="store", dest="showNFibersInSlicer", type=float,
    help='Approximate upper limit on number of fibers to show when MRML scene of clusters is loaded into slicer')

args = parser.parse_args()


if not os.path.exists(args.inputFile):
    print "<wm_label_from_atlas.py> Error: Input file", args.inputFile, "does not exist."
    exit()

if not os.path.isdir(args.atlasDirectory):
    print "Error: Atlas directory", args.atlasDirectory, "does not exist."
    exit()

outdir = args.outputDirectory
if not os.path.exists(outdir):
    print "<wm_label_from_atlas.py> Output directory", outdir, "does not exist, creating it."
    os.makedirs(outdir)

print "<wm_label_from_atlas.py> Starting computation."
print ""
print "=====input file ======\n", args.inputFile
print "=====atlas directory =====\n", args.atlasDirectory
print "=====output directory =====\n", args.outputDirectory
print "=========================="
print ""


if args.numberOfFibers is not None:
    print "fibers to analyze per subject: ", args.numberOfFibers
else:
    print "fibers to analyze per subject: ALL"
number_of_fibers = args.numberOfFibers

if args.fiberLength is not None:
    fiber_length = args.fiberLength
else:
    fiber_length = 25.0
print "minimum length of fibers to analyze (in mm): ", args.fiberLength

if args.numberOfJobs is not None:
    number_of_jobs = args.numberOfJobs
else:
    print 'CPUs detected:', multiprocessing.cpu_count()
    number_of_jobs = multiprocessing.cpu_count()
print 'Using N jobs:', number_of_jobs

if args.flag_verbose:
    print "Verbose ON."
else:
    print "Verbose OFF."
verbose = args.flag_verbose
if args.numberOfClusters is not None:
    number_of_clusters = args.numberOfClusters
else:
    number_of_clusters = 200
print "Number of clusters to find: ", number_of_clusters

if args.distanceThreshold is not None:
    threshold = args.distanceThreshold
else:
    threshold = 0.0
print "Threshold (in mm) for fiber distances: ", threshold

if args.sizeOfNystromSample is not None:
    number_of_sampled_fibers = args.sizeOfNystromSample
else:
    number_of_sampled_fibers = 2000
print "Size of Nystrom sample: ", number_of_sampled_fibers

if args.sigma is not None:
    sigma = args.sigma
else:
    sigma = 60
print "Sigma in mm: ", sigma

if args.showNFibersInSlicer is not None:
    show_fibers = args.showNFibersInSlicer
else:
    show_fibers = 5000.0
print "Maximum total number of fibers to display in MRML/Slicer: ", show_fibers


# default clustering parameters that probably don't need to be changed
# from TMI 2007 paper
use_nystrom=True
distance_method = 'Mean'
use_normalized_cuts = True
number_of_eigenvectors = 10


# another option. was not used in TMI 2007 paper. would need a different sigma.
#distance_method ='Hausdorff'
# This was used in the TMI paper but 10 eigenvectors
# contain almost as much information and reduce noise for single subject clustering
#number_of_eigenvectors = 20

# =======================================================================
# Above this line is argument parsing. Below this line is the pipeline.
# =======================================================================

# read atlas
print "<wm_label_from_atlas.py> Loading input atlas:", args.atlasDirectory
atlas = wma.cluster.load_atlas(args.atlasDirectory, 'atlas')

# read data
print "<wm_label_from_atlas.py> Reading input file:", args.inputFile
pd = wma.io.read_polydata(args.inputFile)
    
# preprocessing step: minimum length
print "<wm_label_from_atlas.py> Preprocessing by length:", fiber_length, "mm."
pd2 = wma.filter.preprocess(pd, fiber_length)

# preprocessing step: fibers to analyze
if number_of_fibers is not None:
    print "<wm_label_from_atlas.py> Downsampling to ", number_of_fibers, "fibers."
    input_data = wma.filter.downsample(pd2, number_of_fibers)
else:
    input_data = pd2

#-----------------
# Label the data
#-----------------
output_polydata_s, cluster_numbers_s, color, embed = \
    wma.cluster.spectral_atlas_label(input_data, atlas)

# Write the polydata with cluster indices saved as cell data
fname_output = os.path.join(outdir, 'clustered_whole_brain.vtp')
wma.io.write_polydata(output_polydata_s, fname_output)

# Figure out file name and mean color for each cluster, and write the individual polydatas
fnames = list()
cluster_colors = list()
number_of_clusters = numpy.max(cluster_numbers_s)
for c in range(number_of_clusters):
    mask = cluster_numbers_s == c
    pd_c = wma.filter.mask(output_polydata_s, mask)
    fname_c = 'cluster_{0:05d}.vtp'.format(c)
    # save the filename for writing into the MRML file
    fnames.append(fname_c)
    # prepend the output directory
    fname_c = os.path.join(outdir, fname_c)
    print fname_c
    wma.io.write_polydata(pd_c, fname_c)
    color_c = color[mask,:]
    cluster_colors.append(numpy.mean(color_c,0))
    
# Estimate subsampling ratio to display approx. show_fibers total fibers
number_fibers = len(cluster_numbers_s)
if number_fibers < show_fibers:
    ratio = 1.0
else:
    ratio = show_fibers / number_fibers
print "<wm_label_from_atlas.py> Total fibers:", number_fibers, "Fibers to show by default:", show_fibers
print "<wm_label_from_atlas.py> Subsampling ratio estimated as:", ratio

# Write the MRML file into the directory where the polydatas were already stored
fname = os.path.join(outdir, 'clustered_tracts.mrml')
wma.mrml.write(fnames, numpy.around(numpy.array(cluster_colors), decimals=3), fname, ratio=ratio)

# View the whole thing in png format for quality control
print '<wm_label_from_atlas.py> Rendering and saving image'
ren = wma.render.render(output_polydata_s, 1000)
ren.save_views(outdir)
del ren

print 'Done labeling subject.'

