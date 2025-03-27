import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

def show_print_summary(file_name, pages_range, color_mode, total_price, job_id):
    """
    Displays the print summary, including file information, and provides a button to proceed to payment.
    """
    summary_window = tk.Toplevel()
    summary_window.title("Printing Summary")
    summary_window.configure(bg="white")
    summary_window.attributes("-fullscreen", True)

    def exit_fullscreen(event):
        summary_window.destroy()

    summary_window.bind("<Escape>", exit_fullscreen)

    main_frame = tk.Frame(summary_window, bg="white")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    try:
        logo_img = Image.open("logo1.jpg")
        logo_img = logo_img.resize((600, 600), Image.Resampling.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_img)

        logo_label = tk.Label(main_frame, image=logo_photo, bg="white")
        logo_label.image = logo_photo
        logo_label.pack(side=tk.LEFT, padx=100, pady=50)

    except FileNotFoundError:
        tk.Label(main_frame, text="Logo not found!", font=("Arial", 16), bg="white", fg="red").pack(side=tk.LEFT, padx=20, pady=20)
    except Exception as e:
        tk.Label(main_frame, text=f"Error loading logo: {e}", font=("Arial", 16), bg="white", fg="red").pack(side=tk.LEFT, padx=20, pady=20)

    content_frame = tk.Frame(main_frame, bg="white")
    content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)

    content_inner_frame = tk.Frame(content_frame, bg="white")
    content_inner_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    tk.Label(content_inner_frame, text=f"File Name: {file_name}", font=("Arial", 24, "bold"), bg="white", fg="red", anchor="w", width=30).pack(pady=10)
    tk.Label(content_inner_frame, text=f"Pages to Print: {pages_range}", font=("Arial", 20), bg="white", fg="black", anchor="w", width=30).pack(pady=10)
    tk.Label(content_inner_frame, text=f"Color Mode: {color_mode.title()}", font=("Arial", 20), bg="white", fg="black", anchor="w", width=30).pack(pady=10)
    tk.Label(content_inner_frame, text=f"Total Price: {total_price} pesos", font=("Arial", 24, "bold"), bg="white", fg="red", anchor="w", width=30).pack(pady=10)

    tk.Frame(content_inner_frame, bg="white").pack(pady=40)  # Spacer

    tk.Button(
        content_inner_frame,
        text="Proceed to Payment",
        font=("Arial", 20),
        bg="red",
        fg="white",
        command=lambda: [summary_window.destroy(), show_payment_screen(total_price, job_id)]
    ).pack(pady=20)

    tk.Label(
        summary_window,
        text="Press ESC to exit",
        font=("Arial", 16),
        bg="white",
        fg="gray"
    ).pack(side=tk.BOTTOM, pady=10)

    summary_window.mainloop()

if __name__ == "__main__":
    # Example call to the print summary function for testing
    sample_file_name = "example_document.pdf"
    sample_pages_range = "1-10"
    sample_color_mode = "colored"
    sample_total_price = 20
    sample_job_id = 123

    show_print_summary(
        file_name=sample_file_name,
        pages_range=sample_pages_range,
        color_mode=sample_color_mode,
        total_price=sample_total_price,
        job_id=sample_job_id
    )
