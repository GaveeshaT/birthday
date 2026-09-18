import os
import zipfile
from io import BytesIO
import base64
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
from streamlit_cropper import st_cropper
import streamlit.components.v1 as components

st.set_page_config(page_title="Automated Birthday Flyer Generator", layout="wide")

st.title("🎉 Automated Birthday Flyer Generator")

# --- 1. Load Master Excel Database ---
excel_file = "Employee_Master.xlsx"

if not os.path.exists(excel_file):
    st.error(f"⚠️ Master Excel file '{excel_file}' not found in the app directory.")
    st.stop()

@st.cache_data
def load_excel(file_path):
    return pd.read_excel(file_path)

df_master = load_excel(excel_file)

# --- 2. Sidebar Layout & Mode Selection ---
st.sidebar.header("⚙️ App Mode & Styling")
app_mode = st.sidebar.radio("Select Mode", ["🎯 Single Flyer Editor", "📦 Bulk Review & Edit"])

backdrop_file = st.sidebar.file_uploader("Upload Backdrop Template (PNG/JPG)", type=["png", "jpg", "jpeg"])
font_color = st.sidebar.color_picker("Pick Font Color", "#1a5276")

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Layout & Position Controls")

photo_x = st.sidebar.slider("Photo X Position", 0, 2000, 230)
photo_y = st.sidebar.slider("Photo Y Position", 0, 2000, 310)
photo_size = st.sidebar.slider("Photo Circle Size", 100, 800, 320)

name_y = st.sidebar.slider("Name Y Position", 0, 2000, 660)
name_font_size = st.sidebar.slider("Name Font Size", 16, 120, 36)

dept_y = st.sidebar.slider("Department Y Position", 0, 2000, 760)
dept_font_size = st.sidebar.slider("Department Font Size", 12, 80, 24)

# Helper function to find excel columns dynamically
def get_excel_columns(df):
    d_col = next((col for col in df.columns if 'display' in col.lower() and 'name' in col.lower()), None)
    if not d_col:
        d_col = next((col for col in df.columns if 'name' in col.lower()), None)
    dep_col = next((col for col in df.columns if 'dept' in col.lower() or 'department' in col.lower()), None)
    path_cols = [col for col in df.columns if 'photo' in col.lower() or 'path' in col.lower() or 'file' in col.lower()]
    return d_col, dep_col, path_cols

display_name_col, dept_col, possible_path_cols = get_excel_columns(df_master)


# ==========================================
# MODE 1: SINGLE FLYER EDITOR
# ==========================================
if app_mode == "🎯 Single Flyer Editor":
    st.markdown("Upload your template, crop the photo into a circle, and save your flyer individually.")
    
    uploaded_photo = st.file_uploader("Upload Birthday Person's Photo", type=["png", "jpg", "jpeg"], key="single_photo")

    if uploaded_photo is not None:
        filename = uploaded_photo.name
        st.info(f"📁 Selected Image Filename: **{filename}**")

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

            if backdrop_file is not None:
                backdrop = Image.open(backdrop_file).convert("RGBA")
                
                final_emp_img = cropped_img.resize((photo_size, photo_size)).convert("RGBA")

                # Circular Mask
                mask = Image.new("L", (photo_size, photo_size), 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0, photo_size, photo_size), fill=255)
                
                circular_img = ImageOps.fit(final_emp_img, mask.size, centering=(0.5, 0.5))
                circular_img.putalpha(mask)

                backdrop.paste(circular_img, (photo_x, photo_y), circular_img)

                draw = ImageDraw.Draw(backdrop)
                font_path = "BrittanySignature.ttf"
                try:
                    if os.path.exists(font_path):
                        font_name = ImageFont.truetype(font_path, name_font_size)
                    else:
                        font_name = ImageFont.truetype("arial.ttf", name_font_size)
                    font_dept = ImageFont.truetype("arial.ttf", dept_font_size)
                except IOError:
                    font_name = ImageFont.load_default()
                    font_dept = ImageFont.load_default()

                # Center Text
                name_bbox = draw.textbbox((0, 0), emp_name, font=font_name)
                name_width = name_bbox[2] - name_bbox[0]
                name_x = (backdrop.width - name_width) // 2
                draw.text((name_x, name_y), emp_name, fill=font_color, font=font_name)

                dept_bbox = draw.textbbox((0, 0), emp_dept, font=font_dept)
                dept_width = dept_bbox[2] - dept_bbox[0]
                dept_x = (backdrop.width - dept_width) // 2
                draw.text((dept_x, dept_y), emp_dept, fill=font_color, font=font_dept)

                st.subheader("👀 Live Flyer Preview")
                st.image(backdrop, use_container_width=True)

                buf = BytesIO()
                backdrop.convert("RGB").save(buf, format="PNG")
                byte_im = buf.getvalue()
                b64_img = base64.b64encode(byte_im).decode()
                safe_filename = f"{emp_name.replace(' ', '_')}_Birthday_Flyer.png"

                save_dialog_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                  .save-btn {{
                    background-color: #ff4b4b; color: white; padding: 12px 24px;
                    font-size: 16px; font-family: sans-serif; font-weight: bold;
                    border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                  }}
                  .save-btn:hover {{ background-color: #e03b3b; }}
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
                      for (let i = 0; i < byteCharacters.length; i++) {{ byteNumbers[i] = byteCharacters.charCodeAt(i); }}
                      const byteArray = new Uint8Array(byteNumbers);
                      const blob = new Blob([byteArray], {{type: 'image/png'}});

                      if ('showSaveFilePicker' in window) {{
                        try {{
                          const handle = await window.showSaveFilePicker({{ suggestedName: filename, types: [{{ description: 'PNG Image', accept: {{ 'image/png': ['.png'] }} }}] }});
                          const writable = await handle.createWritable();
                          await writable.write(blob);
                          await writable.close();
                          return;
                        }} catch (err) {{ if (err.name !== 'AbortError') console.error(err); return; }}
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
                st.warning("⚠️ Please upload a backdrop template image in the sidebar.")
        else:
            st.error(f"❌ Could not find a match for '{filename}' in your Excel database.")


# ==========================================
# MODE 2: BULK REVIEW & EDIT
# ==========================================
elif app_mode == "📦 Bulk Review & Edit":
    st.markdown("Upload multiple employee photos, use the **Previous** and **Next** buttons to inspect each flyer, tweak positions with the sidebar sliders, and download all as a ZIP archive when ready.")

    uploaded_photos = st.file_uploader("Upload Multiple Employee Photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="bulk_review_photos")

    if uploaded_photos:
        if "bulk_idx" not in st.session_state:
            st.session_state.bulk_idx = 0

        # Keep index safely bounded
        if st.session_state.bulk_idx >= len(uploaded_photos):
            st.session_state.bulk_idx = len(uploaded_photos) - 1
        if st.session_state.bulk_idx < 0:
            st.session_state.bulk_idx = 0

        # Navigation Header controls
        col_prev, col_mid, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("⬅️ Previous Flyer", use_container_width=True) and st.session_state.bulk_idx > 0:
                st.session_state.bulk_idx -= 1
                st.rerun()
        with col_mid:
            st.markdown(f"<h4 style='text-align: center; margin-top: 5px;'>Reviewing Flyer {st.session_state.bulk_idx + 1} of {len(uploaded_photos)}</h4>", unsafe_allow_html=True)
        with col_next:
            if st.button("Next Flyer ➡️", use_container_width=True) and st.session_state.bulk_idx < len(uploaded_photos) - 1:
                st.session_state.bulk_idx += 1
                st.rerun()

        current_photo = uploaded_photos[st.session_state.bulk_idx]
        filename = current_photo.name
        st.info(f"📁 Active Filename: **{filename}**")

        match_col = possible_path_cols[0] if possible_path_cols else None
        matched_row = None
        if match_col:
            match_results = df_master[df_master[match_col].astype(str).str.endswith(filename, na=False)]
            if not match_results.empty:
                matched_row = match_results.iloc[0]

        if matched_row is not None:
            emp_name = str(matched_row[display_name_col]) if display_name_col else "Unknown"
            emp_dept = str(matched_row[dept_col]) if dept_col else "Unknown Dept"

            st.success(f"✅ Matched Employee: **{emp_name}** | Department: **{emp_dept}**")

            if backdrop_file is not None:
                # Render preview for the current photo using live sidebar options
                raw_img = Image.open(current_photo).convert("RGBA")
                square_img = ImageOps.fit(raw_img, (photo_size, photo_size), centering=(0.5, 0.5))

                mask = Image.new("L", (photo_size, photo_size), 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0, photo_size, photo_size), fill=255)
                square_img.putalpha(mask)

                backdrop = Image.open(backdrop_file).convert("RGBA")
                backdrop.paste(square_img, (photo_x, photo_y), square_img)

                draw = ImageDraw.Draw(backdrop)
                font_path = "BrittanySignature.ttf"
                try:
                    if os.path.exists(font_path):
                        font_name = ImageFont.truetype(font_path, name_font_size)
                    else:
                        font_name = ImageFont.truetype("arial.ttf", name_font_size)
                    font_dept = ImageFont.truetype("arial.ttf", dept_font_size)
                except IOError:
                    font_name = ImageFont.load_default()
                    font_dept = ImageFont.load_default()

                name_bbox = draw.textbbox((0, 0), emp_name, font=font_name)
                name_width = name_bbox[2] - name_bbox[0]
                name_x = (backdrop.width - name_width) // 2
                draw.text((name_x, name_y), emp_name, fill=font_color, font=font_name)

                dept_bbox = draw.textbbox((0, 0), emp_dept, font=font_dept)
                dept_width = dept_bbox[2] - dept_bbox[0]
                dept_x = (backdrop.width - dept_width) // 2
                draw.text((dept_x, dept_y), emp_dept, fill=font_color, font=font_dept)

                st.image(backdrop, use_container_width=True, caption=f"Live Preview for {emp_name}")

                st.markdown("---")
                st.subheader("📦 Bulk Export Batch")
                st.markdown("Once you have inspected the previews and adjusted your positions via the sidebar sliders, click below to generate and download all flyers together in a ZIP file.")

                if st.button("🚀 Generate & Download All Flyers as ZIP"):
                    zip_buffer = BytesIO()
                    success_count = 0
                    unmatched_files = []

                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for photo_file in uploaded_photos:
                            fname = photo_file.name
                            m_results = df_master[df_master[match_col].astype(str).str.endswith(fname, na=False)]

                            if not m_results.empty:
                                m_row = m_results.iloc[0]
                                e_name = str(m_row[display_name_col]) if display_name_col else "Unknown"
                                e_dept = str(m_row[dept_col]) if dept_col else "Unknown Dept"

                                r_img = Image.open(photo_file).convert("RGBA")
                                s_img = ImageOps.fit(r_img, (photo_size, photo_size), centering=(0.5, 0.5))

                                msk = Image.new("L", (photo_size, photo_size), 0)
                                ImageDraw.Draw(msk).ellipse((0, 0, photo_size, photo_size), fill=255)
                                s_img.putalpha(msk)

                                bg = Image.open(backdrop_file).convert("RGBA")
                                bg.paste(s_img, (photo_x, photo_y), s_img)

                                drw = ImageDraw.Draw(bg)
                                try:
                                    if os.path.exists(font_path):
                                        f_name = ImageFont.truetype(font_path, name_font_size)
                                    else:
                                        f_name = ImageFont.truetype("arial.ttf", name_font_size)
                                    f_dept = ImageFont.truetype("arial.ttf", dept_font_size)
                                except IOError:
                                    f_name = ImageFont.load_default()
                                    f_dept = ImageFont.load_default()

                                n_box = drw.textbbox((0, 0), e_name, font=f_name)
                                n_w = n_box[2] - n_box[0]
                                n_x = (bg.width - n_w) // 2
                                drw.text((n_x, name_y), e_name, fill=font_color, font=f_name)

                                d_box = drw.textbbox((0, 0), e_dept, font=f_dept)
                                d_w = d_box[2] - d_box[0]
                                d_x = (bg.width - d_w) // 2
                                drw.text((d_x, dept_y), e_dept, fill=font_color, font=f_dept)

                                img_byte_arr = BytesIO()
                                bg.convert("RGB").save(img_byte_arr, format="PNG")
                                safe_name = e_name.replace(" ", "_").replace("/", "-")
                                zip_file.writestr(f"{safe_name}_Birthday_Flyer.png", img_byte_arr.getvalue())
                                success_count += 1
                            else:
                                unmatched_files.append(fname)

                    zip_buffer.seek(0)
                    st.success(f"🎉 Successfully packaged **{success_count}** flyers into a ZIP archive!")
                    st.download_button(
                        label="📥 Download ZIP Archive Now",
                        data=zip_buffer,
                        file_name="Birthday_Flyers_Batch.zip",
                        mime="application/zip"
                    )
            else:
                st.warning("⚠️ Please upload a backdrop template image in the sidebar.")
        else:
            st.error(f"❌ Could not find a match for '{filename}' in your Excel master database.")