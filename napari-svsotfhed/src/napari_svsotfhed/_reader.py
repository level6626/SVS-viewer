"""
This module implements a reader plugin for napari that reads SVS files and
displays the image pyramid and the HED mask pyramid.
"""

import numpy as np
import openslide
import dask
import dask.array as da
from openslide import deepzoom as dz


def napari_get_reader(path):
    """A basic implementation of a Reader contribution.

    Parameters
    ----------
    path : str
        Path to file.

    Returns
    -------
    function or None
        If the path is a recognized format, return a function that accepts the
        same path or list of paths, and returns a list of layer data tuples.
    """
    if isinstance(path, list):
        # A path list does not make sense for this plugin
        return None

    # otherwise we return the *function* that can read ``path``.
    if path.endswith(".svs"):
        return reader_function

    return None


def reader_function(path):
    """Take a path or list of paths and return a list of LayerData tuples.

    Readers are expected to return data as a list of tuples, where each tuple
    is (data, [add_kwargs, [layer_type]]), "add_kwargs" and "layer_type" are
    both optional.

    Parameters
    ----------
    path : str
        Path to file.

    Returns
    -------
    layer_data : list of tuples
        A list of LayerData tuples where each tuple in the list contains
        (data, metadata, layer_type), where data is a numpy array, metadata is
        a dict of keyword arguments for the corresponding viewer.add_* method
        in napari, and layer_type is a lower-case string naming the type of
        layer. Both "meta", and "layer_type" are optional. napari will
        default to layer_type=="image" if not provided
    """
    tile_size = 512
    overlap = 0
    # conv matrix
    hed_from_rgb = np.array(
        [
            [1.87798274, -1.00767869, -0.55611582],
            [-0.06590806, 1.13473037, -0.1355218],
            [-0.60190736, -0.48041419, 1.57358807],
        ]
    )

    slide = openslide.open_slide(path)
    gen = dz.DeepZoomGenerator(
        slide, tile_size=tile_size, overlap=overlap, limit_bounds=True
    )
    num_levels = gen.level_count

    @dask.delayed(pure=True)
    def get_tile(level, column, row):
        tile = gen.get_tile(level, (column, row))
        return np.array(tile).transpose((1, 0, 2))

    @dask.delayed(pure=True)
    def get_tile_hed(tile, level, num_levels, threshold=0.05):
        if level == num_levels - 1:
            tile_scaled = tile / 255.0
            hed = separate_stains(tile_scaled[:, :, :3], hed_from_rgb)
            mask = np.zeros((*tile.shape[:2], 3), dtype=np.uint8)
            mask[hed > threshold] = 255
            mask[:, :, 1:] = 0
        else:
            mask = np.zeros((*tile.shape[:2], 3), dtype=np.uint8)
        return mask

    myPyramid = []
    myPyramidHed = []
    # Loop through each level and read the image data
    for level in reversed(range(num_levels)):
        # Get dimensions for the current level
        level_dimensions = gen.level_dimensions[level]

        sample_tile_shape = get_tile(level, 0, 0).shape.compute()
        n_tiles_x, n_tiles_y = gen.level_tiles[level]
        # Remove last tile because it has a custom size.
        if n_tiles_x <= 1 or n_tiles_y <= 1:
            print(
                f"Ignoring Level {level} with dimensions: {level_dimensions}"
            )
            continue
        else:
            print(f"Reading Level {level} with dimensions: {level_dimensions}")
        rows = range(n_tiles_y - 1)
        cols = range(n_tiles_x - 1)

        col_tile = []
        col_mask = []
        for col in cols:
            row_tile = []
            row_mask = []
            for row in rows:
                tile = get_tile(level, col, row)
                tile_mask = get_tile_hed(
                    tile, level, num_levels, threshold=0.05
                )
                row_tile.append(
                    da.from_delayed(tile, sample_tile_shape, np.uint8)
                )
                row_mask.append(
                    da.from_delayed(tile_mask, sample_tile_shape, np.uint8)
                )
            row_tile = da.concatenate(
                row_tile, axis=1, allow_unknown_chunksizes=False
            )
            row_mask = da.concatenate(
                row_mask, axis=1, allow_unknown_chunksizes=False
            )
            col_tile.append(row_tile)
            col_mask.append(row_mask)
        myPyramid.append(
            da.concatenate(col_tile, allow_unknown_chunksizes=False)
        )
        myPyramidHed.append(
            da.concatenate(col_mask, allow_unknown_chunksizes=False)
        )

    # optional kwargs for the corresponding viewer.add_* method
    img_kwargs = {
        "multiscale": True,
        "contrast_limits": [0, 255],
    }
    label_kwargs = {
        "name": "label",
        "multiscale": True,
        "contrast_limits": [0, 255],
    }

    return [
        (myPyramid, img_kwargs, "image"),
        (myPyramidHed, label_kwargs, "image"),
    ]


def separate_stains(rgb, conv_matrix):
    np.maximum(rgb, 1e-6, out=rgb)  # avoiding log artifacts
    log_adjust = np.log(1e-6)  # used to compensate the sum above

    stains = (np.log(rgb) / log_adjust) @ conv_matrix

    np.maximum(stains, 0, out=stains)

    return stains
