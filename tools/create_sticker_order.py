# By Dandy Bouquet, 2025

from pathlib import Path
import yaml
import argparse


def main():
    """Main function to run the script"""
    # Create Argument Parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "PATH", nargs=1,
        help="Path to the order config yaml file")
    parser.add_argument(
        "-p", "--prices", nargs=1,
        help="Path to the prices config yaml file")
    parser.add_argument(
        "-o", "--out", nargs=1,
        help="Path to save the generated order text to")
    parser.add_argument(
        "-s", "--summary", action="store_true",
        help="Add summary info to the end of the order text")
    
    # Parse arguments
    args = parser.parse_args()
    config_path = Path(args.PATH[0])
    output_path = None
    include_summary = args.summary
    prices_path = None
    if args.prices:
        prices_path = args.prices[0]
    if args.out:
        output_path = args.out[0]

    # Load config yaml file
    print(f"Loading order config: {config_path}")
    with open(config_path, "r") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            print(error)
            exit(1)

    # Get settings
    settings = data.get("settings", {})
    root_design_dir = Path(settings.get("design_dir", "."))
    if not root_design_dir.is_absolute():
        root_design_dir = config_path.parent / root_design_dir
    if not root_design_dir.is_dir():
        parser.error(f"Not a directory: {root_design_dir}")
    if "prices_config" in settings:
        prices_path = Path(settings["prices_config"])
    if not prices_path.is_absolute():
        prices_path = config_path.parent / prices_path

    # Load prices yaml file
    print(f"Loading prices config: {config_path}")
    price_config = {}
    with open(prices_path, "r") as stream:
        try:
            price_config = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            print(error)
            exit(1)

    text = ""
    total_price = 0.0
    total_quantity = 0
    total_resale_value = 0.0
    order_list = data["order"]

    header = ["Filename", "Quantity", "Material", "Laminate", "Dimensions"]
    text += "\t".join(header) + "\n"

    # Process each design
    for design_name, design_details in sorted(order_list.items()):
        design_dir = root_design_dir / design_name
        info_path = design_dir / f"{design_name}_info.yaml"

        if info_path.is_file():
            with open(info_path, "r") as stream:
                try:
                    cached_values = yaml.safe_load(stream)
                except yaml.YAMLError as error:
                    print(error)
                    exit(1)
            for key, value in cached_values.items():
                if key not in design_details:
                    design_details[key] = value

        # Populate values from settings into design details where not specified
        for key, value in settings.items():
            if key not in design_details:
                design_details[key] = value

        quantity = design_details["quantity"]
        material = design_details["material"]
        laminate = design_details["laminate"]
        size_inches = design_details["size_inches"]
        total_quantity += quantity
        total_resale_value += design_details["resale_price"] * quantity

        price = 0
        for price_item in price_config["sizes"]:
            if size_inches == price_item["size"]:
                price = price_item["price"] * quantity
        total_price += price

        # text += f"{design_name}\n"
        # text += f"Quantity: {quantity}\n"
        # text += f"Material: {material}\n"
        # text += f"Laminate: {laminate}\n"
        # text += f"Dimensions: {size_inches:.1f} x {size_inches:.1f} inches\n"

        
        text += f"{design_name}\t{quantity}\t{material}\t{laminate}\t{size_inches:.1f} x {size_inches:.1f} \"\n"
        # text += f" * Price: ${price:.2f}\n"
        # text += "\n"

    # Add a summary
    if include_summary:
        text += "\n"
        text += f"Total Designs: {len(order_list)}\n"
        text += f"Total Quantity: {total_quantity}\n"
        text += f"Total Cost: ${total_price:.2f}\n"
        price_per_sticker = total_resale_value / total_quantity
        min_sale_amount = int(total_price / price_per_sticker) + 1
        potential_profit = total_resale_value - total_price
        text += f"Minimum Sell Amount: {min_sale_amount}\n"
        text += f"Total Resale Value: ${total_resale_value:.2f}\n"
        text += f"Potential Profit: ${potential_profit:.2f}\n"

    # Show the order text
    print(text, end="")

    # Save the order text to file
    if output_path:
        print(f"Saving order text to {output_path}")
        with open(output_path, "w") as stream:
            stream.write(text)


if __name__ == "__main__":
    main()
