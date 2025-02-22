# Merch Tools

Utilities for preparing and formatting artwork designs for manufacture as merch.

Current Features:
- Stickers
- Creating sticker orders

By Dandy Bouquet, 2025

# Creating new design

## Pick designs


## Save art images

`_mask.png`
`_art.png`

## Generate cut lines and bleed images

```
python process_stickers.py --preview --config config.yaml design1 design2 design3
```

## Create the .ai file

### Create a new file
Open Adobe Illustrator
Create a new file,
set the width/height to the outputted size in inches from the program

### Add the art
Drag the _full_bleed.png image into the file, set it's Width to the target size, then move it to the side

### Create the cut line
Drag the _cut_mask.png image into the file.
Set it's width to the target size, then move it so it aligns with the canvas
Click the dropdown next to the Image Trace button, then choose Sillouette
Click Embed
Using the select tool, select the 4 corners of the canvas, and delete the control points
Select the cut line path
Change the line width to 1 pt, then set the fill color to transparent

### Finalize
Drag back the art image so it aligns with the canvas.
Save the file


# Preparing an Order

Copy all design .ai files into the order folder

```
cp designs/*/*.ai orders/order1/
```

In the order folder, open each .ai file, click on the art, click Embed, then save/close.

Create the order config .yaml file in the order folder
Specify designs, quantity, material, finish

```
create_sticker_order.py orders/order1/order.yaml --summary
```

The text output can be copy/pasted into an excel sheet to create a table
