from mistralai.client import MistralClient
import fitz  # PyMuPDF
import os

# ==============================
# MISTRAL AI SETUP
# ==============================
api_key = "8G1wusJZc0WG10IVBuzqvrVYIMxOSW2O"  # Replace with your API key
model = "mistral-large-latest"
client = MistralClient(api_key=api_key)

# ==============================
# PDF TEXT EXTRACTION
# ==============================
def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF file using PyMuPDF
    """
    try:
        text = ""
        with fitz.open(pdf_path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text.strip()
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        return None

def get_pdf_file_from_user():
    """
    Get PDF file path from user input
    """
    while True:
        pdf_path = input("📁 Enter the path to your PDF file: ").strip()
        
        # Remove quotes if user drags and drops file
        pdf_path = pdf_path.strip('"\'')
        
        if not os.path.exists(pdf_path):
            print("❌ File not found. Please check the path and try again.")
            continue
            
        if not pdf_path.lower().endswith('.pdf'):
            print("❌ Please provide a PDF file (.pdf extension)")
            continue
            
        return pdf_path

# ==============================
# SUMMARIZATION FUNCTIONS
# ==============================
def get_summary_type_from_user():
    """
    Let user choose summary type
    """
    print("\n📊 Choose summary type:")
    print("1. Concise Summary (2-3 paragraphs)")
    print("2. Detailed Summary (comprehensive)")
    print("3. Bullet Points (key points only)")
    print("4. Executive Summary (1 paragraph)")
    print("5. Custom Focus Summary")
    
    while True:
        choice = input("\nEnter your choice (1-5): ").strip()
        if choice in ['1', '2', '3', '4', '5']:
            return int(choice)
        else:
            print("❌ Please enter a number between 1-5")

def get_custom_focus():
    """
    Get custom focus for summary
    """
    print("\n🎯 What should the summary focus on?")
    print("Examples:")
    print("- Key findings and conclusions")
    print("- Main arguments and evidence")
    print("- Technical specifications")
    print("- Business implications")
    print("- Methodologies used")
    print("- Recommendations and insights")
    
    focus = input("\nEnter your custom focus: ").strip()
    return focus if focus else "main points and key findings"

def create_summary_prompt(text, summary_type, custom_focus=None):
    """
    Create appropriate prompt based on summary type for Mistral AI
    """
    # Truncate text if too long (to avoid token limits)
    if len(text) > 12000:
        text = text[:12000] + "\n\n[Document truncated for length...]"
    
    summary_instructions = {
        1: "Provide a CONCISE summary in 2-3 paragraphs. Focus on the most important information, main points, and key findings. Keep it brief but informative.",
        2: "Provide a DETAILED and comprehensive summary in 4-6 paragraphs. Cover all major sections, arguments, important details, and supporting evidence.",
        3: "Provide a summary in BULLET POINT format. List the key points, main findings, and important information using clear, concise bullet points.",
        4: "Provide an EXECUTIVE SUMMARY in 1 paragraph. Include only the most critical information that would be needed for quick decision-making by senior management.",
        5: f"Provide a focused summary that specifically emphasizes: {custom_focus}. Structure the summary to highlight this aspect while still covering essential information."
    }
    
    instruction = summary_instructions[summary_type]
    
    prompt = f"""
    DOCUMENT TO SUMMARIZE:
    ```text
    {text}
    ```
    
    INSTRUCTIONS:
    {instruction}
    
    Please provide a well-structured, professional summary that accurately captures the essence of the document while being clear and accessible.
    
    IMPORTANT: 
    - Maintain the original meaning and facts
    - Use clear, professional language
    - Structure the summary logically
    - Highlight the most important information
    
    SUMMARY:
    """
    
    return prompt

def generate_summary(text, summary_type, custom_focus=None):
    """
    Generate summary using Mistral AI
    """
    prompt = create_summary_prompt(text, summary_type, custom_focus)
    
    try:
        print("⏳ Generating summary with Mistral AI...")
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        chat_response = client.chat(
            model=model,
            messages=messages
        )
        
        summary = chat_response.choices[0].message.content
        return summary
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        return None

def generate_summary_streaming(text, summary_type, custom_focus=None):
    """
    Generate summary using Mistral AI with streaming
    """
    prompt = create_summary_prompt(text, summary_type, custom_focus)
    
    try:
        print("⏳ Generating summary (streaming)...\n")
        print("=" * 60)
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        full_summary = ""
        print("🤖 Mistral AI: ", end="", flush=True)
        
        for chunk in client.chat_stream(model=model, messages=messages):
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_summary += content
        
        print("\n" + "=" * 60)
        return full_summary
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        return None

# ==============================
# UTILITY FUNCTIONS
# ==============================
def analyze_document_length(text):
    """
    Provide info about document length
    """
    words = len(text.split())
    chars = len(text)
    pages = text.count('\f') + 1  # Rough page count
    print(f"📄 Document stats: {words} words, {chars} characters, approximately {pages} pages")

def save_summary_to_file(summary, original_filename):
    """
    Save summary to text file
    """
    try:
        base_name = os.path.splitext(original_filename)[0]
        output_file = f"{base_name}_summary.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        print(f"💾 Summary saved as: {output_file}")
        return output_file
    except Exception as e:
        print(f"❌ Error saving summary: {e}")
        return None

def display_summary_preview(summary, max_lines=15):
    """
    Show preview of summary
    """
    lines = summary.split('\n')
    print("\n" + "=" * 60)
    print("📋 SUMMARY PREVIEW")
    print("=" * 60)
    
    line_count = 0
    for line in lines:
        if line.strip():
            print(line)
            line_count += 1
            if line_count >= max_lines:
                break
    
    if len([l for l in lines if l.strip()]) > max_lines:
        print("\n... [summary continues] ...")
    
    print("=" * 60)

# ==============================
# MAIN SUMMARIZER FUNCTION
# ==============================
def summarize_single_pdf():
    """
    Main function to summarize a single PDF
    """
    print("=" * 60)
    print("           PDF SUMMARIZER (Mistral AI)")
    print("=" * 60)
    print("This tool uses Mistral AI to generate summaries of PDF documents.")
    print()
    
    # Step 1: Get PDF file from user
    pdf_path = get_pdf_file_from_user()
    filename = os.path.basename(pdf_path)
    print(f"✅ Loaded: {filename}")
    
    # Step 2: Extract text from PDF
    print("📖 Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)
    
    if not text:
        print("❌ Failed to extract text from PDF. The file might be corrupted or scanned.")
        return
    
    if len(text.strip()) < 50:
        print("❌ Very little text extracted. This might be a scanned PDF (image-based).")
        return
    
    # Step 3: Show document stats
    analyze_document_length(text)
    
    # Step 4: Get summary preferences
    summary_type = get_summary_type_from_user()
    custom_focus = None
    
    if summary_type == 5:
        custom_focus = get_custom_focus()
    
    # Step 5: Choose output mode
    print("\n🎯 Choose output mode:")
    print("1. Standard (get full summary at once)")
    print("2. Streaming (see summary as it's generated)")
    
    output_choice = input("Enter choice (1 or 2): ").strip()
    
    # Step 6: Generate summary
    if output_choice == "2":
        summary = generate_summary_streaming(text, summary_type, custom_focus)
    else:
        summary = generate_summary(text, summary_type, custom_focus)
    
    if not summary:
        print("❌ Failed to generate summary.")
        return
    
    # Step 7: Display full results (if not streaming)
    if output_choice != "2":
        display_summary_preview(summary)
    
    # Step 8: Save summary
    save_choice = input("\n💾 Save summary to file? (y/n): ").strip().lower()
    if save_choice in ['y', 'yes']:
        saved_file = save_summary_to_file(summary, filename)
        if saved_file:
            print(f"✅ Summary successfully saved!")
    
    print("\n🎉 Summary completed successfully!")

# ==============================
# BATCH PROCESSING FUNCTION
# ==============================
def summarize_multiple_pdfs():
    """
    Process multiple PDFs in a folder
    """
    print("=" * 60)
    print("       BATCH PDF SUMMARIZER (Mistral AI)")
    print("=" * 60)
    
    folder_path = input("📁 Enter folder path containing PDFs: ").strip()
    folder_path = folder_path.strip('"\'')
    
    if not os.path.exists(folder_path):
        print("❌ Folder not found.")
        return
    
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("❌ No PDF files found in the folder.")
        return
    
    print(f"\n📚 Found {len(pdf_files)} PDF files:")
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"  {i}. {pdf_file}")
    
    summary_type = get_summary_type_from_user()
    custom_focus = None
    
    if summary_type == 5:
        custom_focus = get_custom_focus()
    
    summaries = []
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
        print(f"\n{'='*50}")
        print(f"📄 Processing: {pdf_file}")
        print(f"{'='*50}")
        
        text = extract_text_from_pdf(pdf_path)
        if text and len(text.strip()) > 50:
            summary = generate_summary(text, summary_type, custom_focus)
            if summary:
                summaries.append((pdf_file, summary))
                display_summary_preview(summary, 6)
                save_summary_to_file(summary, pdf_file)
            else:
                print("❌ Failed to generate summary for this file")
        else:
            print("❌ Skipped - unable to extract sufficient text")
    
    print(f"\n🎉 Batch processing completed! Processed {len(summaries)} files successfully.")

# ==============================
# QUICK SUMMARY FUNCTION
# ==============================
def quick_summary(pdf_path, summary_type=1):
    """
    Quick summary function for programmatic use
    """
    text = extract_text_from_pdf(pdf_path)
    if text and len(text.strip()) > 50:
        return generate_summary(text, summary_type)
    return None

# ==============================
# PROGRAM ENTRY POINT
# ==============================
if __name__ == "__main__":
    try:
        print("🤖 Mistral AI PDF Summarizer")
        print("1. Summarize single PDF")
        print("2. Summarize multiple PDFs in folder")
        print("3. Quick summary (for developers)")
        
        choice = input("\nChoose option (1, 2, or 3): ").strip()
        
        if choice == "1":
            summarize_single_pdf()
        elif choice == "2":
            summarize_multiple_pdfs()
        elif choice == "3":
            pdf_path = input("Enter PDF path for quick summary: ").strip()
            summary = quick_summary(pdf_path)
            if summary:
                print("\n" + "=" * 60)
                print("QUICK SUMMARY:")
                print("=" * 60)
                print(summary)
        else:
            print("❌ Invalid choice. Running single PDF mode...")
            summarize_single_pdf()
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("\n💡 Installation requirements:")
        print("pip install mistralai pymupdf")

# ==============================
# USAGE EXAMPLES AND DOCUMENTATION
# ==============================
"""
USAGE EXAMPLES:

1. Interactive Single PDF:
   python mistral_summarizer.py
   > Choose 1
   > Enter PDF path
   > Choose summary type

2. Batch Processing:
   python mistral_summarizer.py
   > Choose 2
   > Enter folder path

3. Programmatic Use:
   from mistral_summarizer import quick_summary
   summary = quick_summary("document.pdf")

FEATURES:
✅ Uses Mistral Large model for high-quality summaries
✅ Multiple summary types (concise, detailed, bullet points, etc.)
✅ Streaming output option
✅ Batch processing for multiple PDFs
✅ Custom focus summaries
✅ Professional formatting
✅ Error handling and user-friendly interface

INSTALLATION:
pip install mistralai pymupdf
"""