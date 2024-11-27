import argparse
import fitz

def split_long_pages_avoid_splitting_content(input_pdf_path, output_pdf_path):
    doc = fitz.open(input_pdf_path)
    new_doc = fitz.open()

    # A4 aspect ratio: height / width
    a4_aspect_ratio = 297 / 210  # Approximately 1.41429

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        width, height = page.rect.width, page.rect.height
        desired_height = width * a4_aspect_ratio

        if height <= desired_height:
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        else:
            split_positions = extract_split_positions(page, desired_height)

            # Split the page using the calculated positions
            for i in range(len(split_positions) - 1):
                top = split_positions[i]
                bottom = split_positions[i + 1]

                # Validate and debug split positions
                if not (0 <= top < bottom <= height):
                    print(f"Skipping invalid split: top={top}, bottom={bottom}, height={height}")
                    continue
                
                current_page_height = bottom - top
                if current_page_height <= 50:
                    continue

                rect = fitz.Rect(0, top, width, bottom)
                new_page = new_doc.new_page(width=width, height=current_page_height)

                # Copy the content from the original page to the new page
                try:
                    new_page.show_pdf_page(new_page.rect, doc, page_num, clip=rect)
                    print("Saved content to new page: {page_num}.{i}")
                except Exception as e:
                    print(f"Error copying content to new page: {e}")
                    continue

    new_doc.save(output_pdf_path)

def extract_split_positions(page, desired_height):
    height = page.rect.height
    blocks = page.get_text("blocks")
    # Each block is (x0, y0, x1, y1, "text", block_no)
    # Collect all y positions of content
    y_positions = []

    for block in blocks:
        y0 = block[1]
        y1 = block[3]
        y_positions.append((y0, y1))

    # Collect image positions
    images = page.get_images(full=True)
    for img in images:
        img_rect = page.get_image_bbox(img)
        y0 = img_rect.y0
        y1 = img_rect.y1
        y_positions.append((y0, y1))

    # Sort content ranges by their vertical positions
    y_positions.sort()

    # Initialize split positions
    split_positions = [0.0]
    current_y = 0.0

    while current_y < height:
        target_y = current_y + desired_height

        # Adjust target_y if it exceeds the page height
        if target_y > height:
            target_y = height

        # Define a tolerance for adjusting the split position
        tolerance = desired_height * 0.1  # 10% of desired height
        min_y = max(current_y, target_y - tolerance)
        max_y = min(height, target_y + tolerance)

        # Find the largest whitespace within the tolerance range
        free_spaces = []
        occupied_ranges = []

        # Build occupied ranges within the min_y and max_y
        for y0, y1 in y_positions:
            if y1 <= min_y or y0 >= max_y:
                continue
            occupied_ranges.append((max(y0, min_y), min(y1, max_y)))

        # If there are no occupied ranges, the whole area is free
        if not occupied_ranges:
            free_spaces.append((min_y, max_y))
        else:
            # Start with the entire range and subtract occupied ranges
            occupied_ranges.sort()
            last_end = min_y
            for y0, y1 in occupied_ranges:
                if y0 > last_end:
                    free_spaces.append((last_end, y0))
                last_end = max(last_end, y1)
            if last_end < max_y:
                free_spaces.append((last_end, max_y))

        # Find the largest free space
        largest_free_space = None
        max_free_height = 0
        for y0, y1 in free_spaces:
            free_height = y1 - y0
            if free_height > max_free_height:
                max_free_height = free_height
                largest_free_space = (y0, y1)

        # Determine the split position
        if largest_free_space:
            split_y = (largest_free_space[0] + largest_free_space[1]) / 2
        else:
            # No adequate free space; split at the target position
            split_y = target_y

        # Append the split position and update current_y
        if split_y >= height:
            split_y = height
        split_positions.append(split_y)
        current_y = split_y

    # Remove duplicate positions and sort them
    split_positions = sorted(set(split_positions))
    
    return split_positions

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("i", help="Path to input file")
    parser.add_argument("o", help="Path to output file")
    args = parser.parse_args()

    print(f"Input file: {args.i}")
    print(f"Output file: {args.o}")
    
    split_long_pages_avoid_splitting_content(args.i, args.o)

if __name__ == "__main__":
    main()