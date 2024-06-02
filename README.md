# SVS-viewer

## Set up the environment.
`conda create -n Napari python=3.9`
### Install TensorFlow
`mamba install -c conda-forge tensorflow-gpu=2.10`
### Install Napari
`mamba install napari pyqt`
### Install opensilde
```
mamba install -c conda-forge openslide
mamba install -c conda-forge openslide-python
```
### Install StarDist
`pip install stardist`

## Plugins
### preloadsvs
Preload svs data into memory with openslide.
It took 90s to load the 100MB test image:
`TCGA-AK-3440-01Z-00-DX1.ea0763b1-4262-4c75-9f76-080af1ffeab7.svs`
To install, run `python -m pip install -e .` in ./preloadsvs/.
### svsotf
An On-The-Fly reader of svs data with the help of Dask [https://docs.dask.org/en/stable/].
It took 3s to load the 100MB test image:
`TCGA-AK-3440-01Z-00-DX1.ea0763b1-4262-4c75-9f76-080af1ffeab7.svs`
It took 7s to load the 1000MB test image:
`TCGA-CZ-4863-01Z-00-DX1.7f3da3a1-5d70-4d30-a9f3-80ab883cf9f6.svs`
To install, run `python -m pip install -e .` in ./svsotf/.
### svsotfhed
Further apply `rgb2hed` preprocessing in scikit-image to identify nuclei when we are zoomed in enough. in the On-The-Fly reader.
To install, run `python -m pip install -e .` in ./svsotfhed/.
### svsmodel
Further apply StarDist [https://github.com/stardist/stardist/] to identify nuclei when we are zoomed in enough. in the On-The-Fly reader.
To install, run `python -m pip install -e .` in ./svsmodel/.
