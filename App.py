import csv
import io
import sys
from tkinter import messagebox, font
from tkinterdnd2 import DND_FILES, TkinterDnD
import aprslib
import tk

def parse_csv(input_data, is_file=True) -> list:
    parsed_data = []

    # If input_data is a file path, open the file. Otherwise, treat input_data as bytes and use StringIO
    if is_file:
        # Open the file for reading
        with open(input_data, mode='r', encoding='utf-8') as csv_file:
            parsed_data = parse_csv_content(csv_file)
    else:
        # Treat input_data as bytes, decode to string, and use StringIO to simulate a file
        csv_string = io.StringIO(input_data.decode('utf-8'))
        parsed_data = parse_csv_content(csv_string)

    return parsed_data

def parse_csv_content(csv_content) -> list:
    parsed_data = []
    # Create a CSV reader object
    csv_reader = csv.DictReader(csv_content)

    # Iterate over each row in the CSV file
    for row in csv_reader:
        # Extract the 'From', 'To', and 'Data UTF-8' fields
        from_field = row['From']
        to_field = row['To']
        data_utf8_field = row['Data UTF-8']

        # Append the extracted data to the list
        parsed_data.append({
            'From': from_field,
            'To': to_field,
            'Data UTF-8': data_utf8_field,
            'Date': row['Date'],
            'Time': row['Time'],
        })

    return parsed_data

def google_maps_link(datapoint: dict) -> str:
	if not 'longitude' in datapoint or not 'latitude' in datapoint:
		raise ValueError("Datapoint does not contain longitude and latitude")

	return f"https://www.google.com/maps/place/{datapoint['latitude']}N+{datapoint['longitude']}E"

def default_maps_link(datapoint: dict) -> str:
	if not 'longitude' in datapoint or not 'latitude' in datapoint:
		raise ValueError("Datapoint does not contain longitude and latitude")

	return f"geo:{datapoint['latitude']},{datapoint['longitude']}"

def get_last_datapoint(csv_file_path: str):
	parsed_data = parse_csv(csv_file_path)
	latest_working_datapoint = None
	for data in parsed_data:
		joined = f"{data['From']}>{data['To']}:{data['Data UTF-8']}"
		pkg = aprslib.parse(joined)

		try:
			_ = google_maps_link(pkg)
			latest_working_datapoint = pkg
		except ValueError:
			print(f"Skipping data without LAT/LON values: {data}")
			continue

	return latest_working_datapoint

import tkinter as tk
from tkinter import ttk
import qrcode
from PIL import Image, ImageTk

def create_qr_code(link):
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill='black', back_color='white')
    return img


def display_qr_code(window, datapoint):
    # Set the minimum size of the window
    window.minsize(800, 600)

    # Configure the window's grid or pack to expand
    window.grid_columnconfigure(0, weight=1)
    window.grid_rowconfigure(0, weight=1)

    def refresh_ui(datapoint):
        # Clear existing content in the window
        for widget in window.winfo_children():
            widget.destroy()

        if datapoint is None:
            # Just show the thing that a file should be dropped
            large_font = font.Font(size=36)
            ttk.Label(window, text="Drop an exported CSV from SDRangel here.\nLike directly on the text, I have no idea\nhow to make it accept it on the whole window", font=large_font).pack(pady=50, padx=50)
            return

        # Create QR codes for Google Maps and default maps
        qr_img_google_maps = create_qr_code(google_maps_link(datapoint))
        qr_img_default_maps = create_qr_code(default_maps_link(datapoint))  # Assuming a function to generate this link

        # Convert QR code images to a format tkinter can use
        tk_img_google_maps = ImageTk.PhotoImage(qr_img_google_maps)
        tk_img_default_maps = ImageTk.PhotoImage(qr_img_default_maps)

        # Create a main frame for QR codes with a white background
        qr_frame = ttk.Frame(window, padding="10", relief="solid")
        qr_frame.pack(padx=20, pady=20)

        # Create a frame for the Google Maps QR code
        google_maps_frame = ttk.Frame(qr_frame, padding="10")
        google_maps_frame.pack(side="left", padx=10)
        ttk.Label(google_maps_frame, text="Google Maps Link", font=font.Font(size=20)).pack()
        label_google_maps = ttk.Label(google_maps_frame, image=tk_img_google_maps)
        label_google_maps.image = tk_img_google_maps  # keep a reference!
        label_google_maps.pack()

        # Create a frame for the Default Maps QR code
        default_maps_frame = ttk.Frame(qr_frame, padding="10")
        default_maps_frame.pack(side="left", padx=10)
        ttk.Label(default_maps_frame, text="Default Maps App", font=font.Font(size=20)).pack()
        label_default_maps = ttk.Label(default_maps_frame, image=tk_img_default_maps)
        label_default_maps.image = tk_img_default_maps  # keep a reference!
        label_default_maps.pack()

        # Display latitude and longitude
        lat_lon_frame = ttk.Frame(window, padding="10")
        lat_lon_frame.pack(pady=(0, 20))
        ttk.Label(lat_lon_frame, text=f"Latitude: {datapoint['latitude']}"  , font=font.Font(size=20)).pack()
        ttk.Label(lat_lon_frame, text=f"Longitude: {datapoint['longitude']}", font=font.Font(size=20)).pack()

        # Add a box (one can copy from) that contains the raw str()
        raw_frame = ttk.Frame(window, padding="10")
        raw_frame.pack(pady=(0, 20))
        ttk.Label(raw_frame, text="Raw APRS Data").pack()
        raw_text = tk.Text(raw_frame, height=5, width=50)
        raw_text.insert(tk.END, str(datapoint))
        raw_text.configure(state='disabled')
        raw_text.pack()

        # Display a text that says "Drop in a new file to update"
        ttk.Label(window, text="Drop in a new file to update", font=font.Font(size=20)).pack(pady=(0, 20))


    def on_file_drop(event):
        try:
            file_path = event.data
            new_datapoint = get_last_datapoint(file_path)
            if new_datapoint is None:
                messagebox.showerror("Error", "No datapoint found in the CSV file.")
                return
            refresh_ui(new_datapoint)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process the file: {e}")

    # Set up drag-and-drop file handling
    window.drop_target_register(DND_FILES)
    window.dnd_bind('<<Drop>>', on_file_drop)

    refresh_ui(datapoint)
    window.mainloop()

# if we have arguments, already parse the file
datapoint = None
if len(sys.argv) > 1:
    try:
        datapoint = get_last_datapoint(sys.argv[1])
    except Exception as e:
        print(f"Failed to process the file: {e}")


window = TkinterDnD.Tk()
window.title("Finding the Balloon among us")
display_qr_code(window, datapoint)
