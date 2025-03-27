import time
import tkinter as tk
from threading import Thread
import mysql.connector  # Import MySQL Connector
import subprocess
import os
from PIL import Image, ImageTk
from tkinter import messagebox  # Import messagebox for alert popups



def convert_docx_to_pdf(docx_file_path):
    """Convert .docx file to .pdf using LibreOffice in headless mode."""
    pdf_file_path = docx_file_path.replace(".docx", ".pdf")
    try:
        subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", docx_file_path], check=True)
        print(f"[DEBUG] Converted {docx_file_path} to {pdf_file_path}.")
        return pdf_file_path
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to convert {docx_file_path} to PDF: {e}")
        return None

def print_file(job_id):
    """Fetch file data and send it to the printer with appropriate settings."""
    try:
        connection = mysql.connector.connect(
            host="paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com",
            user="admin",
            password="paperazzi",
            database="paperazzi"
        )
        cursor = connection.cursor()

        select_query = """
            SELECT p.document_name, p.file_data, j.pages_to_print, j.color_mode
            FROM print_jobs p
            JOIN print_job_details j ON p.job_id = j.job_id
            WHERE p.job_id = %s
        """
        cursor.execute(select_query, (job_id,))
        result = cursor.fetchone()

        def get_printer_list():
            try:
                result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, check=True)
                return [line.split()[1] for line in result.stdout.splitlines() if line.startswith("printer")]
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Could not retrieve printer list: {e}")
                return []

        printer_name = "Canon_TS200_series_1"
        available_printers = get_printer_list()
        if printer_name not in available_printers:
            print(f"[ERROR] Printer {printer_name} not found. Available printers: {available_printers}")
            return

        if result:
            document_name, file_data, pages_to_print, color_mode = result
            temp_file_path = f"/tmp/{document_name}"

            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(file_data)
            print(f"[DEBUG] File saved at {temp_file_path}.")

            if temp_file_path.endswith(".docx"):
                pdf_file_path = convert_docx_to_pdf(temp_file_path)
                if pdf_file_path:
                    temp_file_path = pdf_file_path
                else:
                    print("[ERROR] PDF conversion failed. Aborting print.")
                    return

            page_range = None if pages_to_print.lower() == "all" else pages_to_print
            color_option = "ColorModel=RGB" if color_mode.lower() == "colored" else "ColorModel=Gray"

            command = ["lp", "-d", printer_name, "-o", color_option, temp_file_path]
            if page_range:
                command.insert(3, "-P")
                command.insert(4, page_range)

            print(f"[DEBUG] Sending command to printer: {command}")
            subprocess.run(command, check=True)
            print(f"[DEBUG] File {temp_file_path} sent to the printer successfully.")

            os.remove(temp_file_path)
            print(f"[DEBUG] Temporary file {temp_file_path} deleted.")
        else:
            print(f"[ERROR] No file found for job ID {job_id}.")
    except mysql.connector.Error as e:
        print(f"[ERROR] Database error: {e}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Printer error: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def update_job_status(job_id):
    """Updates the status of a print job to 'complete' in the database and triggers printing."""
    try:
        connection = mysql.connector.connect(
            host="paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com",
            user="admin",
            password="paperazzi",
            database="paperazzi"
        )
        cursor = connection.cursor()

        update_query = "UPDATE print_job_details SET status = %s, updated_at = NOW() WHERE job_id = %s"
        cursor.execute(update_query, ("complete", job_id))
        connection.commit()

        print(f"[DEBUG] Job ID {job_id} marked as complete in the database.")
        print_file(job_id)
    except mysql.connector.Error as e:
        print(f"[ERROR] Error updating job status: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def show_payment_screen(total_price, job_id):
    """Displays the payment screen and handles coin detection and printing."""
    root = tk.Tk()
    root.title("Payment Screen")
    root.attributes("-fullscreen", True)
    root.configure(bg="white")
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{screen_width}x{screen_height}+0+0")
    root.overrideredirect(1)

    def exit_fullscreen(event):
        root.destroy()
    total_amount = 0
    timeout = 300

    def cancel_print_job():
        try:
            connection = mysql.connector.connect(
                host="paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com",
                user="admin",
                password="paperazzi",
                database="paperazzi"
            )
            cursor = connection.cursor()

            query1 = "UPDATE print_jobs SET status = %s WHERE job_id = %s"
            cursor.execute(query1, ("failed", job_id))
            query2 = "UPDATE print_job_details SET status = %s WHERE job_id = %s"
            cursor.execute(query2, ("cancelled", job_id))
            connection.commit()

            messagebox.showinfo("Cancelled", "The print job has been cancelled.")
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Failed to cancel print job: {err}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
            GPIO.cleanup()
            if root.winfo_exists():
                root.destroy()
            subprocess.run(["python3", "frame1.py"], check=True)

    cancel_button = tk.Button(root, text="Cancel", command=cancel_print_job, bg="red", fg="white", font=("Arial", 14))
    cancel_button.place(relx=0.9, rely=0.9, anchor="center")

    def calculate_amount(pulse_count):
        return pulse_count

    def update_gui(message, color="black"):
        status_label.config(text=message, fg=color)

    def timeout_handler():
        nonlocal total_amount
        if total_amount < total_price:
            update_gui("Payment timed out. Resetting...", "red")
            root.after(2000, root.destroy)
            GPIO.cleanup()
            subprocess.run(["python3", "frame1.py"], check=True)

    def print_job():
        try:
            connection = mysql.connector.connect(
                host="paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com",
                user="admin",
                password="paperazzi",
                database="paperazzi"
            )
            cursor = connection.cursor()
            update_query = """
                UPDATE print_job_details
                SET inserted_amount = %s, updated_at = NOW()
                WHERE job_id = %s
            """
            cursor.execute(update_query, (total_amount, job_id))
            connection.commit()
            print(f"[DEBUG] Final inserted amount for Job ID {job_id} recorded as {total_amount} pesos.")
        except mysql.connector.Error as e:
            print(f"[ERROR] Database error while updating inserted amount: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
