import os
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
from streamlit_cropper import st_cropper
import streamlit.components.v1 as components
import base64

st.set_page_config(page_title="Automated Birthday Flyer Generator", layout="wide")

st.title("🎉 Automated Birthday Flyer Generator")
st.markdown("Upload your template, crop into a circle, customize styles, and use the save dialog button to choose your download location.")

# --- 1. Load Master Excel Database ---
excel_file = "Employee_Master.xlsx"

if not os.path.exists(excel_file):
    st.error(f"⚠️ Master Excel file '{excel_file}' not found in the app directory.")
    st.stop()

@st.cache_data
def load_excel(file_path):
    return pd.read_excel(file_path)

df_master = load_excel(excel_file)

# --- 2. Sidebar Layout & Live Position Controls ---
st.sidebar.header("🎨 Flyer Design & Editor")
backdrop_file = st.sidebar.file_uploader("Upload Backdrop Template (PNG/JPG)", type=["png", "jpg", "jpeg"])
font_color = st.sidebar.color_picker("Pick Font Color", "#1a5276")

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Live Position Controls")

photo_x = st.sidebar.slider("Photo X Position", 0, 2000, 230)
photo_y = st.sidebar.slider("Photo Y Position", 0, 2000, 310)
photo_size = st.sidebar.slider("Photo Circle Size", 100, 800, 320)

name_y = st.sidebar.slider("Name Y Position", 0, 2000, 660)
name_font_size = st.sidebar.slider("Name Font Size", 16, 120, 36)

dept_y = st.sidebar.slider("Department Y Position", 0, 2000, 760)
dept_font_size = st.sidebar.slider("Department Font Size", 12, 80, 24)

# --- 3. Main Interface ---
uploaded_photo = st.file_uploader("Upload Birthday Person's Photo", type=["png", "jpg", "jpeg"])

if uploaded_photo is not None:
    filename = uploaded_photo.name
    st.info(f"📁 Selected Image Filename: **{filename}**")

    # Match Filename with Excel
    display_name_col = next((col for col in df_master.columns if 'display' in col.lower() and 'name' in col.lower()), None)
    if not display_name_col:
        display_name_col = next((col for col in df_master.columns if 'name' in col.lower()), None)
        
    dept_col = next((col for col in df_master.columns if 'dept' in col.lower() or 'department' in col.lower()), None)
    possible_path_cols = [col for col in df_master.columns if 'photo' in col.lower() or 'path' in col.lower() or 'file' in col.lower()]

    matched_row = None
    if possible_path_cols:
        match_col = possible_path_cols[0]
        match_results = df_master[df_master[match_col].astype(str).str.endswith(filename, na=False)]
        if not match_results.empty:
            matched_row = match_results.iloc[0]

    if matched_row is not None:
        emp_name = str(matched_row[display_name_col]) if display_name_col else "Unknown Name"
        emp_dept = str(matched_row[dept_col]) if dept_col else "Unknown Department"
        
        st.success("✅ Match Found in Excel!")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Display Name", emp_name)
        with c2:
            st.metric("Department", emp_dept)

        st.markdown("---")
        st.subheader("🖼️ Crop Photo into Circle")
        
        raw_img = Image.open(uploaded_photo)
        cropped_img = st_cropper(
            raw_img, 
            realtime_update=True, 
            aspect_ratio=(1, 1), 
            return_type='image', 
            key="rho_crop"
        )

        # --- 4. Live Flyer Generation Rendering ---
        if backdrop_file is not None:
            backdrop = Image.open(backdrop_file).convert("RGBA")
            
            # Resize cropped output dynamically using slider value
            final_emp_img = cropped_img.resize((photo_size, photo_size)).convert("RGBA")

            # Create Circular Mask
            mask = Image.new("L", (photo_size, photo_size), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, photo_size, photo_size), fill=255)
            
            circular_img = ImageOps.fit(final_emp_img, mask.size, centering=(0.5, 0.5))
            circular_img.putalpha(mask)

            # Paste photo based on live sidebar sliders
            backdrop.paste(circular_img, (photo_x, photo_y), circular_img)

            # Draw Text dynamically with Brittany Signature Font Support
            draw = ImageDraw.Draw(backdrop)
            
            font_path = "BrittanySignature.ttf"
            try:
                if os.path.exists(font_path):
                    # Use Brittany Signature font for the employee name
                    font_name = ImageFont.truetype(font_path, name_font_size)
                else:
                    font_name = ImageFont.truetype("arial.ttf", name_font_size)
                
                # Department uses standard clean font for readability
                font_dept = ImageFont.truetype("arial.ttf", dept_font_size)
            except IOError:
                font_name = ImageFont.load_default()
                font_dept = ImageFont.load_default()

            # Center Name Horizontally
            name_bbox = draw.textbbox((0, 0), emp_name, font=font_name)
            name_width = name_bbox[2] - name_bbox[0]
            name_x = (backdrop.width - name_width) // 2
            draw.text((name_x, name_y), emp_name, fill=font_color, font=font_name)

            # Center Department Horizontally
            dept_bbox = draw.textbbox((0, 0), emp_dept, font=font_dept)
            dept_width = dept_bbox[2] - dept_bbox[0]
            dept_x = (backdrop.width - dept_width) // 2
            draw.text((dept_x, dept_y), emp_dept, fill=font_color, font=font_dept)

            # Show Live Preview
            st.subheader("👀 Live Flyer Preview")
            st.markdown("Adjust any slider in the sidebar. The preview updates instantly across the canvas.")
            st.image(backdrop, use_container_width=True)

            # Prepare image data as base64 string for JavaScript Save File Picker
            from io import BytesIO
            buf = BytesIO()
            backdrop.convert("RGB").save(buf, format="PNG")
            byte_im = buf.getvalue()
            b64_img = base64.b64encode(byte_im).decode()

            safe_filename = f"{emp_name.replace(' ', '_')}_Birthday_Flyer.png"

            # Custom HTML/JS component to trigger native OS "Save As" file browser dialog
            save_dialog_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <style>
              .save-btn {{
                background-color: #ff4b4b;
                color: white;
                padding: 12px 24px;
                font-size: 16px;
                font-family: sans-serif;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: background 0.2s;
              }}
              .save-btn:hover {{
                background-color: #e03b3b;
              }}
            </style>
            </head>
            <body>
              <button class="save-btn" onclick="saveFileAs()">📥 Save Flyer As...</button>
              
              <script>
                async function saveFileAs() {{
                  const base64Data = "{b64_img}";
                  const filename = "{safe_filename}";
                  
                  const byteCharacters = atob(base64Data);
                  const byteNumbers = new Array(byteCharacters.length);
                  for (let i = 0; i < byteCharacters.length; i++) {{
                      byteNumbers[i] = byteCharacters.charCodeAt(i);
                  }}
                  const byteArray = new Uint8Array(byteNumbers);
                  const blob = new Blob([byteArray], {{type: 'image/png'}});

                  if ('showSaveFilePicker' in window) {{
                    try {{
                      const options = {{
                        suggestedName: filename,
                        types: [{{
                          description: 'PNG Image',
                          accept: {{ 'image/png': ['.png'] }}
                        }}]
                      }};
                      const handle = await window.showSaveFilePicker(options);
                      const writable = await handle.createWritable();
                      await writable.write(blob);
                      await writable.close();
                      return;
                    }} catch (err) {{
                      if (err.name !== 'AbortError') {{
                        console.error(err);
                      }} else {{
                        return;
                      }}
                    }}
                  }}

                  const link = document.createElement('a');
                  link.href = URL.createObjectURL(blob);
                  link.download = filename;
                  link.click();
                }}
              </script>
            </body>
            </html>
            """

            components.html(save_dialog_html, height=70)

        else:
            st.warning("⚠️ Please upload a backdrop template image in the sidebar to render the flyer.")
    else:
        st.error(f"❌ Could not find a match for '{filename}' in your Excel master database.")