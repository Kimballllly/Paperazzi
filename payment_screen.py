import RPi.GPIO as GPIO
import time
import tkinter as tk
from threading import Thread
import mysql.connector  # Import MySQL Connector
import subprocess
import os

# GPIO setup
COIN_PIN = 26  # The GPIO pin connected to the COIN wire
GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Use internal pull-up resistor

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

    """

    Fetches the file data and name associated with the job_id from the print_jobs table,

    fetches pages_to_print and color_mode from the print_job_details table, saves it as a 

    temporary file, converts it to PDF if needed, and sends it to the printer with the appropriate color settings.

    """

    try:

        # Database connection

        connection = mysql.connector.connect(

            host="paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com",

            user="admin",

            password="paperazzi",

            database="paperazzi"

        )

        cursor = connection.cursor()



        # Fetch file data, document name, pages_to_print, and color_mode

        select_query = """

            SELECT p.document_name, p.file_data, j.pages_to_print, j.color_mode

            FROM print_jobs p

            JOIN print_job_details j ON p.job_id = j.job_id

            WHERE p.job_id = %s

        """

        cursor.execute(select_query, (job_id,))

        result = cursor.fetchone()



        if result:

            document_name, file_data, pages_to_print, color_mode = result

            temp_file_path = f"/tmp/{document_name}"  # Save the file in a temporary directory



            # Write file data to a temporary file

            with open(temp_file_path, "wb") as temp_file:

                temp_file.write(file_data)

            print(f"[DEBUG] File saved at {temp_file_path}.")



            # Convert .docx to .pdf if the file is in .docx format

            if temp_file_path.endswith(".docx"):

                pdf_file_path = convert_docx_to_pdf(temp_file_path)

                if pdf_file_path:

                    temp_file_path = pdf_file_path  # Use the PDF file for printing

                else:

                    print("[ERROR] PDF conversion failed. Aborting print.")

                    return



            # Determine page range (if specific pages are provided or "all")

            if pages_to_print.lower() == "all":

                page_range = None  # No page range argument needed for all pages

            else:

                page_range = pages_to_print  # Specific pages like "1-4", "2-2", etc.



            # Determine the color mode

            if color_mode.lower() == "colored":

                color_option = "ColorModel=RGB"  # Color printing

            elif color_mode.lower() == "bw" or color_mode.lower() == "monochrome":

                color_option = "ColorModel=Gray"  # Black-and-white printing

            else:

                print(f"[ERROR] Invalid color mode: {color_mode}")

                return



            # Base command to print the document with the specified color mode

            command = ["lp", "-d", "Canon_TS200_series_1", "-o", color_option, temp_file_path]



            # Add page range to the command if provided

            if page_range:

                command.insert(2, "-P")  # Insert the -P option for page range

                command.insert(3, page_range)  # Insert the page range itself





            print(f"[DEBUG] Sending command to printer: {command}")

            subprocess.run(command, check=True)

            print(f"[DEBUG] File {temp_file_path} sent to the printer successfully.")



            # Clean up temporary files (both original and PDF)

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
    """
    Updates the status of a print job to 'complete' in the database and triggers printing.
    """
    try:

        connection = mysql.connector.connect(
            host="paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com",
            user="admin",
            password="paperazzi",
            database="paperazzi"
        )

        cursor = connection.cursor()

        # Update query
        update_query = "UPDATE print_job_details SET status = %s, updated_at = NOW() WHERE job_id = %s"
        cursor.execute(update_query, ("complete", job_id))
        connection.commit()


        print(f"[DEBUG] Job ID {job_id} marked as complete in the database.")


        # Trigger the print job



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
    root.configure(bg="white")  # Set the background to white

    total_amount = 0
    timeout = 300  # Timeout in seconds (5 minutes)

    def calculate_amount(pulse_count):
        """Calculate the amount in pesos based on the pulse count."""
        return pulse_count  # 1 pulse = 1 peso

    def update_gui(message, color="black"):
        """Update the GUI labels with dynamic messages."""
        status_label.config(text=message, fg=color)

    def timeout_handler():
        """Handle timeout if no coins are inserted."""
        nonlocal total_amount
        if total_amount < total_price:
            update_gui("Payment timed out. Resetting...", "red")
            root.after(2000, root.destroy)  # Close the GUI after 2 seconds
            GPIO.cleanup()
            try:
                subprocess.run(["python3", "frame1.py"], check=True)
            except Exception as e:
                print(f"[ERROR] Error launching frame1.py: {e}")

    def print_job():
        """Start the print job and monitor its progress."""
        try:
            update_gui("Printing in progress...", "blue")
            print_file(job_id)  # Trigger the print job

            # Monitor print job status
            while True:
                result = subprocess.run(
                    ["lpstat", "-o"], capture_output=True, text=True
                )
                if job_id not in result.stdout:
                    break  # Print job is no longer in the queue
                time.sleep(2)  # Check every 2 seconds

            update_gui("Print complete. Returning to main menu.", "green")
            time.sleep(2)  # Allow the user to see the message
            root.destroy()
            subprocess.run(["python3", "frame1.py"], check=True)

        except subprocess.CalledProcessError as e:
            update_gui("Printer error occurred.", "red")
            print(f"[ERROR] Printing error: {e}")
        except Exception as e:
            print(f"[ERROR] Unexpected error during printing: {e}")
        finally:
            GPIO.cleanup()

    def coin_detection():
        """Detect coin pulses and update the total amount."""
        nonlocal total_amount
        pulse_count = 0
        last_state = GPIO.input(COIN_PIN)

        try:
            while total_amount < total_price:
                current_state = GPIO.input(COIN_PIN)

                # Detect falling edge (pulse detection)
                if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                    pulse_count += 1
                    total_amount = calculate_amount(pulse_count)
                    root.after(0, update_gui, f"Inserted Amount: {total_amount} pesos", "black")

                    remaining_amount = total_price - total_amount
                    if remaining_amount <= 0:
                        root.after(0, update_gui, "Payment Complete!", "green")
                        Thread(target=print_job, daemon=True).start()
                        break

                last_state = current_state
                time.sleep(0.01)  # Check every 10 ms

        except RuntimeError as e:
            print(f"[ERROR] GPIO error: {e}")
        except KeyboardInterrupt:
            print("\n[DEBUG] Exiting.")
        finally:
            GPIO.cleanup()

    # GUI setup
    header_label = tk.Label(
        root,
        text="Insert Coins to Complete Payment",
        font=("Helvetica", 36, "bold"),
        bg="white",
        fg="black",
    )
    header_label.pack(pady=30)

    amount_label = tk.Label(
        root,
        text="Inserted Amount: 0 pesos",
        font=("Helvetica", 28),
        bg="white",
        fg="black",
    )
    amount_label.pack(pady=20)

    status_label = tk.Label(
        root,
        text=f"Remaining: {total_price} pesos",
        font=("Helvetica", 28),
        bg="white",
        fg="red",
    )
    status_label.pack(pady=20)

    footer_label = tk.Label(
        root,
        text="Thank you for using our service!",
        font=("Helvetica", 20),
        bg="white",
        fg="gray",
    )
    footer_label.pack(side="bottom", pady=20)

    # Ensure GPIO is set before starting the thread
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    except RuntimeError as e:
        print(f"[ERROR] GPIO initialization error: {e}")
        return

    # Run the coin detection in a separate thread
    coin_thread = Thread(target=coin_detection, daemon=True)
    coin_thread.start()

    # Start the timeout timer
    root.after(timeout * 1000, timeout_handler)

    root.mainloop()


if __name__ == "__main__":
    # Example call to the payment screen function for testing
    show_payment_screen(total_price=20, job_id="12345")
