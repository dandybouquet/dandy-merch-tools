# By Dandy Bouquet, 2025

import imageio
import numpy
from matplotlib import pyplot
from pathlib import Path
import yaml
import skfmm
import skimage.measure
import skimage.morphology
import argparse


def expand_edge(mask_image: numpy.array, thickness: float) -> numpy.array:
    """Expands the edges of a mask image by the given thickness."""
    phi = numpy.where(numpy.int64(mask_image), -0.5, 0.5)
    signed_distance = skfmm.distance(phi, dx = 1)
    return (signed_distance <= thickness)


def adjust_image_size(matrix: numpy.array, bbox: tuple, target_size_px: int,
                      pad_value):
    """
    Adjust the size of an image to the target size in pixels by adding padding
    around the edges.
    """
    bbox_x, bbox_y, bbox_width, bbox_height = bbox
    pad_x1 = (target_size_px - bbox_width) // 2
    pad_y1 = (target_size_px - bbox_height) // 2
    pad_x2 = (target_size_px - bbox_width) - pad_x1
    pad_y2 = (target_size_px - bbox_height) - pad_y1
    padding = [(pad_y1, pad_y2), (pad_x1, pad_x2)]
    dims = len(matrix.shape)
    if dims == 3:
        padding.append((0, 0))
    source_pixels = matrix[bbox_y : bbox_y + bbox_height,
                           bbox_x : bbox_x + bbox_width]
    return numpy.pad(source_pixels, padding, constant_values=pad_value)


def find_smallest_size(size: float, size_list: list):
    """
    Get the smallest available size in a size list that can fit the given size.
    """
    for size_to_check in sorted(size_list):
        if size < size_to_check:
            return size_to_check
    raise ValueError(
        f"Size is too large! No available sizes can fit {size:.1f}")


def main():
    """Main function to run the script"""

    default_settings = {
        "thickness": 0.0625,  # 1/16"
        "bleed_thickness": 0.0625,  # 1/16"
        "min_corner_radius": 0.03125,  # 1/32"
        "alpha_threshold": 100,
        "design_dir": ".",  # Same directory as the config yaml file
        "sizes": numpy.arange(1, 10 + 0.5, 0.5).tolist(),
    }
    
    # Color constants
    white_transparent = (255, 255, 255, 0)
    black_opaque = (0, 0, 0, 255)
    gray_opaque = (128, 128, 128, 255)

    # Create Argument Parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "DESIGNS", nargs="*",
        help=("List of design names to process. Processes all designs if not "
              "specified"))
    parser.add_argument(
        "-p", "--preview", action="store_true",
        help="Show design previews in a window")
    parser.add_argument(
        "-c", "--config", nargs=1, default=["./config.yaml"],
        help="Path to config yaml file")

    # Parse arguments
    args = parser.parse_args()
    design_name_list = args.DESIGNS
    show_preview = args.preview
    config_path = Path(args.config[0])

    # Load config file
    print(f"Loading config: {config_path}")
    with open(config_path, "r") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            print(error)
            exit(1)
    
    # Load settings, with default
    settings = data.get("settings", {})
    for key, value in default_settings.items():
        if key not in settings:
            settings[key] = value

    # Validate design directory
    root_design_dir = Path(settings.get("design_dir", "."))
    if not root_design_dir.is_absolute():
        root_design_dir = config_path.parent / root_design_dir
    if not root_design_dir.is_dir():
        parser.error(f"Not a directory: {root_design_dir}")

    alpha_threshold = settings["alpha_threshold"]
    thickness_inches = settings["thickness"]
    bleed_thickness_inches = settings["bleed_thickness"]
    size_list = settings["sizes"]

    # Process each design
    for design_name, design_details in data["designs"].items():
        if design_name_list and design_name not in design_name_list:
            continue
        print(f"Processing design: {design_name}")

        # Populate values from settings into design details where not specified
        for key, value in settings.items():
            if key not in design_details:
                design_details[key] = value

        # Design paths
        design_dir = root_design_dir / design_name
        art_path = design_dir / f"{design_name}_art.png"
        mask_path = design_dir / f"{design_name}_mask.png"
        full_bleed_path = design_dir / f"{design_name}_full_bleed.png"
        cut_mask_path = design_dir / f"{design_name}_cut_mask.png"
        if "art" in design_details:
            art_path = design_dir / Path(design_details["art"])
        if "mask" in design_details:
            mask_path = design_dir / design_details.get("mask", art_path)
        elif not mask_path.is_file():
            mask_path = art_path
        print(f"  Path: {design_dir}")

        if "width" not in design_details:
            print("  Width not specified, defaulting to 300 dpi")
            width_inches = None
        else:
            width_inches = design_details["width"]

        # Load images
        print(f"  Loading art: {art_path.name}")
        color_image = numpy.array(imageio.v3.imread(art_path))
        print(f"  Loading mask: {mask_path.name}")
        mask_image = numpy.array(imageio.v3.imread(mask_path))
        _, width, _ = color_image.shape
        dpi = (width / width_inches)
        print(f"  DPI = {dpi:.0f} px/inch")

        # Add margins around the edge
        # Not really needed if enough margin in art image?
        # padding = int((thickness_inches + bleed_thickness_inches) * dpi * 1.5)
        # print(f"  Adding {padding} pixels of margin")
        # padding = ((padding, padding), (padding, padding), (0, 0))
        # color_image = numpy.pad(color_image, padding, constant_values=0)
        # mask_image = numpy.pad(mask_image, padding, constant_values=0)
        # _, width, _ = color_image.shape

        thickness = thickness_inches * dpi
        bleed_thickness = bleed_thickness_inches * dpi
        min_corner_radius = settings["min_corner_radius"] * dpi

        # Differentiate the inside / outside region
        art_mask = (mask_image[:,:,3] > alpha_threshold)

        # Create the cut mask
        # Start by growing the mask by thickness plus the corner radius
        print("  Creating cut mask with thickness "
              f"{thickness_inches:.4f}\" ({thickness:.0f} px)")
        outside_mask = ~expand_edge(art_mask, thickness + min_corner_radius)

        # Remove holes by finding negative space regions, then filling them
        # This ignores the largest region, which is the outside background
        label = skimage.measure.label(numpy.int64(outside_mask))
        regions = skimage.measure.regionprops(label)
        regions = sorted(regions, key=lambda x: -x.num_pixels)
        for props in regions[1:]:
            outside_mask[tuple(props.coords.T)] = False
        print(f"    Removed {len(regions) - 1} holes")

        # Now shrink the oustide mask by the min corner radius to obtain the
        # final cut mask
        cut_mask = ~expand_edge(outside_mask, min_corner_radius)

        # Cut contour is a pixel preview of the cut line around the cut mask
        cut_contour = skimage.morphology.binary_dilation(cut_mask) ^ cut_mask

        # Cut mask is the area inside the full bleed area. Everything outside
        # the bleed mask will be transparent in the final art image
        print("  Creating full bleed mask with bleed thickness "
              f"{bleed_thickness_inches}\" ({int(bleed_thickness)} px)")
        bleed_mask = expand_edge(cut_mask, bleed_thickness)
        
        # Get a bounding box around the source artwork mask
        print("  Computing bounding box")
        label = skimage.measure.label(numpy.int64(bleed_mask))
        regions = skimage.measure.regionprops(label)
        bbox = (regions[0].bbox[1], regions[0].bbox[0],
                regions[0].bbox[3] - regions[0].bbox[1],
                regions[0].bbox[2] - regions[0].bbox[0])
        art_size_px = max(bbox[2], bbox[3])

        # Resize the image so that it fits to the nearest available square size
        # This will make it easier to fit into an Illustrator file
        art_size_inches = art_size_px / dpi
        print(f"    Full bleed size = {art_size_inches:.1f}\" ({art_size_px} px)")
        target_size_inches = find_smallest_size(art_size_inches, size_list)
        print(f"  Placing image into {target_size_inches:.1f}\" square")
        target_size_px = int(target_size_inches * dpi)
        color_image = adjust_image_size(
            color_image, bbox, target_size_px, pad_value=0)
        bleed_mask = adjust_image_size(
            bleed_mask, bbox, target_size_px, pad_value=False)
        cut_mask = adjust_image_size(
            cut_mask, bbox, target_size_px, pad_value=False)
        cut_contour = adjust_image_size(
            cut_contour, bbox, target_size_px, pad_value=False)

        # Save the full bleed image, which is the artwork masked to the full
        # bleed area
        print(f"  Saving full bleed image: {full_bleed_path.name}")
        full_bleed_image = color_image.copy()
        full_bleed_image[~bleed_mask, :] = white_transparent
        full_bleed_path = design_dir / f"{design_name}_full_bleed.png"
        imageio.imwrite(full_bleed_path, full_bleed_image)

        # Save the cut mask image, which can be used in Illustrator to trace a
        # cut line using the Image Trace tool
        print(f"  Saving cut mask image: {cut_mask_path.name}")
        cut_mask_image = color_image.copy()
        cut_mask_image[~cut_mask] = white_transparent
        cut_mask_image[cut_mask] = black_opaque
        cut_mask_path = design_dir / f"{design_name}_cut_mask.png"
        imageio.imwrite(cut_mask_path, cut_mask_image)

        # Create plot with preview of cut lines and bleed
        print(f"  Saving preview")
        preview = color_image.copy()
        preview[~bleed_mask, :] = gray_opaque
        preview[cut_contour, :] = black_opaque
        _, ax = pyplot.subplots()
        ax.set_title(f"{design_name} ({target_size_inches:.1f}\", {dpi:.0f} DPI)")
        ax.set_xlabel("X (inches)")
        ax.set_ylabel("Y (inches)")
        ax.imshow(preview, origin="upper",
                  extent=(0, target_size_inches, target_size_inches, 0))
        preview_path = design_dir / f"{design_name}_preview.png"
        pyplot.savefig(str(preview_path))

        # Save an info yaml file
        export = {
            "name": design_name,
            "dpi": dpi,
            "size_inches": target_size_inches,
            "size_pixels": target_size_px,
        }
        info_path = design_dir / f"{design_name}_info.yaml"
        print(f"  Saving {info_path.name}")
        with open(info_path, "w") as stream:
            yaml.dump(export, stream, default_flow_style=False)

        # Show preview plot in a window
        if show_preview:
            print(f"  Showing preview")
            pyplot.show()


if __name__ == "__main__":
    main()
