import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk  # type: ignore
import fitz  # type: ignore  # PyMuPDF for PDF preview
import sys
import io
from docx import Document # type: ignore
import mysql.connector  # type: ignore
from print_summary import show_print_summary  # type: ignore # Import the function
from print_summary import show_payment_screen


# Database connection function
def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host="paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com",
            user="admin",
            password="paperazzi",
            database="paperazzi"
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None


def update_job_status(job_id, new_status, details=None):
    connection = connect_to_database()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        query = "UPDATE print_jobs SET status = %s WHERE job_id = %s"
        cursor.execute(query, (new_status, job_id))

        # Optionally log details in a separate column if provided
        if details:
            details_query = "UPDATE print_jobs SET details = %s WHERE job_id = %s"
            cursor.execute(details_query, (str(details), job_id))

        connection.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error updating job status: {err}")
        return False
    finally:
        connection.close()


def start_print_job(file_name, pages_range, color_mode):
    try:
        # Calculate the total number of pages
        if pages_range == "all":
            pages_to_print = int(total_pages)
        else:
            start_page, end_page = map(int, pages_range.split('-'))
            pages_to_print = end_page - start_page + 1

        # Determine price per page based on color mode
        price_per_page = 3 if color_mode == "bw" else 5
        total_price = pages_to_print * price_per_page

        # Save job details to database
        connection = connect_to_database()
        if not connection:
            messagebox.showerror("Error", "Failed to connect to the database for saving job details.")
            return

        cursor = connection.cursor()
        query = """
            INSERT INTO print_job_details (job_id, file_name, total_pages, pages_to_print, color_mode, total_price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (job_id, file_name, total_pages, pages_range, color_mode, total_price, 'processing'))
        connection.commit()
        connection.close()

        # Confirmation message
        messagebox.showinfo("Print Job Started", f"Print job for {file_name} has started.\nTotal price: {total_price} pesos.")
        
        # Optionally, update job status after the printing process completes
        update_job_status(job_id, "completed")  # Change to "failed" if the printing fails

    except Exception as e:
        messagebox.showerror("Error", f"Failed to start print job: {e}")


def start_printing_options(file_name, file_path, total_pages, job_id):
    def start_printing():
        selected_pages = pages_var.get()
        color_option = color_var.get()

        if selected_pages == "range":
            try:
                start_page = int(start_page_var.get())
                end_page = int(end_page_var.get())
                if start_page < 1 or end_page > int(total_pages) or start_page > end_page:
                    raise ValueError("Invalid page range.")
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid page range: {e}")
                return
            pages_range = f"{start_page}-{end_page}"
            pages_to_print = end_page - start_page + 1
        else:
            pages_range = "all"
            pages_to_print = int(total_pages)

        # Calculate the price
        price_per_page = 3 if color_option == "bw" else 5
        total_price = pages_to_print * price_per_page

        # Save details to the database
        connection = connect_to_database()
        if not connection:
            messagebox.showerror("Error", "Failed to connect to the database for saving job details.")
            return

        try:
            cursor = connection.cursor()

            # Insert the print job details into the `print_job_details` table
            query = """
                INSERT INTO print_job_details (job_id, file_name, total_pages, pages_to_print, color_mode, total_price, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            cursor.execute(query, (job_id, file_name, total_pages, pages_range, color_option, total_price, 'processing'))
            connection.commit()
        except mysql.connector.Error as e:
            messagebox.showerror("Error", f"Failed to save print job details: {e}")
            return
        finally:
            connection.close()

        # Show the print summary
        show_print_summary(file_name, pages_range, color_option, total_price, job_id)

        # Optionally, update job status to "processing"
        if not update_job_status(job_id, "processing"):
            messagebox.showerror("Error", "Failed to update job status to processing.")

    # Cancel printing function
    def cancel_printing():
        if messagebox.askyesno("Confirm", "Cancel this print job?"):
            if update_job_status(job_id, "failed"):  # Use "failed" instead of "cancelled"
                messagebox.showinfo("Cancelled", "The print job has been cancelled.")
                root.quit()
                # Return to frame1 or main screen
            else:
                messagebox.showerror("Error", "Failed to update print job status.")

    def increment_start_page():
        current = int(start_page_var.get())
        if current < int(total_pages):
            start_page_var.set(current + 1)

    def decrement_start_page():
        current = int(start_page_var.get())
        if current > 1:
            start_page_var.set(current - 1)

    def increment_end_page():
        current = int(end_page_var.get())
        if current < int(total_pages):
            end_page_var.set(current + 1)

    def decrement_end_page():
        current = int(end_page_var.get())
        if current > 1:
            end_page_var.set(current - 1)

    def load_preview():
        connection = connect_to_database()
        if not connection:
            messagebox.showerror("Error", "Failed to connect to the database for file preview.")
            return

        try:
            cursor = connection.cursor()
            query = "SELECT file_data FROM print_jobs WHERE job_id = %s"
            cursor.execute(query, (job_id,))
            result = cursor.fetchone()

            if not result or not result[0]:
                preview_canvas.create_text(
                    375, 500, text="File not found in database", font=("Arial", 16), fill="black"
                )
                return

            file_data = result[0]  # BLOB data

            if file_name.endswith(('.png', '.jpg', '.jpeg')):  # Image file
                img = Image.open(io.BytesIO(file_data))
                img.thumbnail((750, 1000))
                img_tk = ImageTk.PhotoImage(img)
                preview_canvas.create_image(375, 500, image=img_tk)
                preview_canvas.image = img_tk
            elif file_name.endswith('.pdf'):  # PDF file
                pdf_document = fitz.open(stream=file_data, filetype="pdf")
                page = pdf_document[0]  # First page
                pix = page.get_pixmap()  # Render page to an image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.thumbnail((750, 1000))
                img_tk = ImageTk.PhotoImage(img)
                preview_canvas.create_image(375, 500, image=img_tk)
                preview_canvas.image = img_tk
                pdf_document.close()
            else:
                preview_canvas.create_text(
                    375, 500, text="Preview not available", font=("Arial", 16), fill="black"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load preview: {e}")
        finally:
            connection.close()

    root = tk.Tk()
    root.title("Printing Options")
    root.configure(bg="white")
    root.attributes("-fullscreen", True)  # Fullscreen mode

    def exit_fullscreen(event):
        root.destroy()

    root.bind("<Escape>", exit_fullscreen)  # Exit fullscreen with Escape key

    # Main Frame
    main_frame = tk.Frame(root, bg="white")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Left Frame - File Preview
    left_frame = tk.Frame(main_frame, width=900, bg="white")
    left_frame.pack(side="left", fill="both", padx=10, pady=10)

    preview_label = tk.Label(left_frame, text="File Preview", font=("Arial", 20, "bold"), bg="white")
    preview_label.pack(pady=10, padx=10)
    preview_canvas = tk.Canvas(left_frame, width=750, height=1000, bg="lightgray")
    preview_canvas.pack(pady=5, padx=5)

    # Load the preview
    load_preview()

    # Right Frame - Options
    right_frame = tk.Frame(main_frame, width=900, bg="white")
    right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    # Logo
    try:
        logo_img = Image.open("logo.jpg")
        logo_img.thumbnail((250, 250))
        logo_tk = ImageTk.PhotoImage(logo_img)
        logo_label = tk.Label(right_frame, image=logo_tk, bg="white")
        logo_label.image = logo_tk
        logo_label.pack(pady=10, anchor="center")
    except Exception as e:
        tk.Label(right_frame, text="Logo not found", bg="white", font=("Arial", 16), fg="red").pack(pady=10)

    # File details
    file_details_frame = tk.Frame(right_frame, bg="white")
    file_details_frame.pack(fill="x", padx=20, pady=10)

    file_name_label = tk.Label(file_details_frame, text="File Name: ", font=("Arial", 18, "bold"), bg="white", anchor="w")
    file_name_label.grid(row=0, column=0, sticky="w")
    file_name_value = tk.Label(file_details_frame, text=file_name, font=("Arial", 18), bg="white", anchor="w")
    file_name_value.grid(row=0, column=1, sticky="w")

    total_pages_label = tk.Label(file_details_frame, text="Total Pages: ", font=("Arial", 18, "bold"), bg="white", anchor="w")
    total_pages_label.grid(row=1, column=0, sticky="w")
    total_pages_value = tk.Label(file_details_frame, text=total_pages, font=("Arial", 18), bg="white", anchor="w")
    total_pages_value.grid(row=1, column=1, sticky="w")

    # Styling for Pages to Print Section
    pages_section = tk.Frame(right_frame, bg="#f4f4f4", padx=10, pady=10, relief="solid", borderwidth=2)
    pages_section.pack(fill="x", pady=20)

    pages_label = tk.Label(pages_section, text="Pages to Print", font=("Arial", 18, "bold"), bg="#f4f4f4")
    pages_label.pack(pady=10)

    pages_var = tk.StringVar(value="all")
    color_var = tk.StringVar(value="colored")

    all_pages_radio = tk.Radiobutton(pages_section, text="All Pages", variable=pages_var, value="all", font=("Arial", 14), bg="#f4f4f4")
    all_pages_radio.pack(anchor="w")
    range_pages_radio = tk.Radiobutton(pages_section, text="Page Range", variable=pages_var, value="range", font=("Arial", 14), bg="#f4f4f4")
    range_pages_radio.pack(anchor="w")

    page_range_frame = tk.Frame(pages_section, bg="#f4f4f4")
    page_range_frame.pack(fill="x", pady=5)

    start_page_var = tk.StringVar(value="1")
    start_page_label = tk.Label(page_range_frame, text="Start Page", font=("Arial", 14), bg="#f4f4f4")
    start_page_label.grid(row=0, column=0)
    start_page_entry = tk.Entry(page_range_frame, textvariable=start_page_var, font=("Arial", 14), width=5)
    start_page_entry.grid(row=0, column=1)

    decrement_start_button = tk.Button(page_range_frame, text="-", font=("Arial", 14), width=2, command=decrement_start_page)
    decrement_start_button.grid(row=0, column=2)
    increment_start_button = tk.Button(page_range_frame, text="+", font=("Arial", 14), width=2, command=increment_start_page)
    increment_start_button.grid(row=0, column=3)

    end_page_var = tk.StringVar(value=total_pages)
    end_page_label = tk.Label(page_range_frame, text="End Page", font=("Arial", 14), bg="#f4f4f4")
    end_page_label.grid(row=1, column=0)
    end_page_entry = tk.Entry(page_range_frame, textvariable=end_page_var, font=("Arial", 14), width=5)
    end_page_entry.grid(row=1, column=1)

    decrement_end_button = tk.Button(page_range_frame, text="-", font=("Arial", 14), width=2, command=decrement_end_page)
    decrement_end_button.grid(row=1, column=2)
    increment_end_button = tk.Button(page_range_frame, text="+", font=("Arial", 14), width=2, command=increment_end_page)
    increment_end_button.grid(row=1, column=3)

    # Styling for Color Mode Section
    color_section = tk.Frame(right_frame, bg="#f4f4f4", padx=10, pady=10, relief="solid", borderwidth=2)
    color_section.pack(fill="x", pady=20)

    color_mode_label = tk.Label(color_section, text="Color Mode", font=("Arial", 18, "bold"), bg="#f4f4f4")
    color_mode_label.pack(pady=10)

    colored_radio = tk.Radiobutton(color_section, text="Colored", variable=color_var, value="colored", font=("Arial", 14), bg="#f4f4f4")
    colored_radio.pack(anchor="w")
    black_white_radio = tk.Radiobutton(color_section, text="Black and White", variable=color_var, value="bw", font=("Arial", 14), bg="#f4f4f4")
    black_white_radio.pack(anchor="w")

    # Action Buttons
    action_buttons_frame = tk.Frame(right_frame, bg="white")
    action_buttons_frame.pack(fill="x", pady=10)

    cancel_button = tk.Button(action_buttons_frame, text="Cancel", command=cancel_printing, font=("Arial", 16), bg="red", fg="white")
    cancel_button.pack(side="left", padx=10, pady=10)

    start_button = tk.Button(action_buttons_frame, text="Start Printing", command=start_printing, font=("Arial", 16), bg="green", fg="white")
    start_button.pack(side="right", padx=10, pady=10)

    root.mainloop()



# Entry point for this script
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python printingoptions.py <file_name> <file_path> <total_pages> <job_id>")
        sys.exit(1)

    file_name = sys.argv[1]
    file_path = sys.argv[2]
    total_pages = sys.argv[3]
    job_id = sys.argv[4]

    start_printing_options(file_name, file_path, total_pages, job_id)
