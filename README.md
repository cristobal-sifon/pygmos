# `PyGMOS`
An automated `PyRAF` data reduction pipeline for `GMOS` spectroscopic data


### Requirements

The best way to install all the requirements (for both `IRAF` and `Python`) is to follow the instructions on the [Gemini website](http://www.gemini.edu/node/12665). Note that IRAF/PyRAF require `Python 2.7` rather than the generally recommended `Python 3.x`. 

## Installation

Download the latest (stable) version from this repository. Then run:

    python setup.py install [--user]

where the `--user` flag is recommended so as not to install as root. To check whether the `pygmos` executable is in your `PATH`, type

    which pygmos

If you see nothing (or a 'not found' message), it means the location of the executable is not part of your `PATH`. If this is the case, look through the installation messages for the place where the executable was copied to. In my case:

    Installing pygmos script to /u/sifon/.local/bin

You should therefore add the equivalent of `/u/sifon/.local/bin` to your `PATH`. Add the following line to your `~/.bashrc` or `~/.bash_profile`:

    export PATH=/u/sifon/.local/bin:$PATH

or to the `~/.cshrc`, etc, if you're not using `bash`:

    setenv PATH /u/sifon/.local/bin:$PATH

and restart the console.

## To run:

First, make sure you activate the `conda` environment (let's assume it's called `gemini`):

    source activate gemini

This should be done every time a new shell session is started. After this, the code is ready to do its magic:

    pygmos <object> [options]

To see available options, type

    pygmos -h

----

**How it works:**

The pipeline takes the object name given in the command line and finds
all data associated with that object. It bias-subtracts all images and
calibrates the science image with the flat field. It then does the
wavelength calibration, removes cosmic rays using L.A.Cosmic (van
Dokkum, 2001, PASP, 113, 1420; distributed with permission) and sky
subtracts the spectra. After this, the individual exposures are added.
Finally, the 1d spectra are extracted.

**Data format taken by pygmos:**

Usual GMOS FITS files, which means a set of exposures per object, each of
which is composed of a science image, a flat field and a calibration
arc.

**When running the pipeline, keep in mind that:**

  * As of now, the pipeline reduces both MOS and longslit GMOS spectra
 but flux calibration is not implemented.
  * Being an automated process, some things could go
 wrong. Most task parameters have to be modified by digging into the
 code, although some of the most important are easy to find, as they
 are in the definition of the functions. Others can be easily added
 in the usual IRAF way.
  * This code has only been tested (and is recommended) for redshift
 measurements.

## Features:

  * Automatic identification of all relevant files given the object name.
  * Incorporates the Lagrangian Cosmic Ray Removal "L.A.Cosmic" code
 implemented by P. van Dokkum (distributed with permission).
  * Can be executed either in automatic or interactive mode, which allows
 for a more thorough analysis, without the need to run each PyRAF task
 separately.
  * Has the option of automatically cutting the spectra and copying them
 to a separate folder. This is useful if, for instance, the spectra
 will be cross-correlated using RVSAO, which takes only single spectra
 (as opposed to multi-slit images) as input.
  * Has the option of aligning the 2d images, which is particularly
 useful for visualizing galaxy cluster data.
 
## Current specific limitations:

  * Flux calibration is not implemented.
  * There is no automated search for the bias file(s). The (master)
 bias file needs to be given in the command (see help page). If not
 given, the pipeline will ask for one.
  * The inventory only finds one Flat and one Arc per observation.
  * When run automatically, the pipeline only extracts one aperture from
 each slit, while some slits might contain more than one object.
  * The interactive feature runs all tasks interactively, without being
 able to switch individual tasks as automatic and others as
 interactive. 
 
 
 ---
 
 (c) Cristóbal Sifón
 
 Last updated October 2017.
