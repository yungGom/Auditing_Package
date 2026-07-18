"""PDF 이름변경 · 도장찍기 도구"""
import streamlit as st
import pandas as pd
import os, tempfile, zipfile
from io import BytesIO

st.set_page_config(page_title="PDF 도구", page_icon="📄", layout="wide")
st.title("📄 PDF 이름변경 · 도장찍기")
st.caption("PDF 파일명 일괄 변경 + 도장 이미지 삽입 + 페이지 번호(BC-XX) 표기")

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
    st.error("PyMuPDF가 설치되어 있지 않습니다. 터미널에서 `pip install PyMuPDF`를 실행해주세요.")

if HAS_FITZ:
    tab1, tab2, tab3 = st.tabs(["① 파일명 추출/변경", "② 도장 + 번호 찍기", "③ 전체 실행"])

    with tab1:
        st.subheader("PDF 파일명 일괄 변경")
        st.markdown("PDF 파일들을 업로드 → AFTER 편집 → 변경된 파일 ZIP 다운로드")
        pdfs = st.file_uploader("PDF 파일 업로드 (여러 개)", type=["pdf"], accept_multiple_files=True, key="rename_pdfs")
        if pdfs:
            names = [f.name for f in pdfs]
            df = pd.DataFrame({"BEFORE": names, "AFTER": names})
            st.markdown("**AFTER 열을 편집하세요:**")
            edited = st.data_editor(df, use_container_width=True, num_rows="fixed", key="rename_editor")
            if st.button("이름 변경 후 다운로드 (ZIP)", type="primary", key="rename_run"):
                with tempfile.TemporaryDirectory() as tmp:
                    for i, pdf in enumerate(pdfs):
                        new_name = str(edited.iloc[i]["AFTER"]).strip()
                        if not new_name.lower().endswith(".pdf"): new_name += ".pdf"
                        with open(os.path.join(tmp, new_name), "wb") as f: f.write(pdf.read())
                    zip_buf = BytesIO()
                    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for fname in os.listdir(tmp): zf.write(os.path.join(tmp, fname), fname)
                    zip_buf.seek(0)
                    st.success(f"✅ {len(pdfs)}개 파일 이름 변경 완료")
                    st.download_button("📥 ZIP 다운로드", data=zip_buf, file_name="renamed_pdfs.zip", mime="application/zip", use_container_width=True)

    with tab2:
        st.subheader("도장 이미지 + 페이지 번호 삽입")
        stamp_pdfs = st.file_uploader("PDF 파일 업로드", type=["pdf"], accept_multiple_files=True, key="stamp_pdfs")
        stamp_img = st.file_uploader("도장 이미지 업로드", type=["png","jpg","jpeg"], key="stamp_img")
        if stamp_pdfs and stamp_img:
            st.markdown("**도장 설정:**")
            c1, c2, c3, c4 = st.columns(4)
            sx = c1.number_input("X 위치", value=0, step=10, key="sx")
            sy = c2.number_input("Y 위치", value=0, step=10, key="sy")
            ss = c3.number_input("도장 크기", value=100, step=10, key="ss")
            fs = c4.number_input("텍스트 크기", value=14, step=1, key="fs")
            if st.button("도장 + 번호 찍기", type="primary", key="stamp_run"):
                stamp_bytes = stamp_img.read()
                with tempfile.TemporaryDirectory() as tmp:
                    stamp_path = os.path.join(tmp, "stamp.png")
                    with open(stamp_path, "wb") as f: f.write(stamp_bytes)
                    results = []
                    for pdf_file in stamp_pdfs:
                        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
                        base_name = os.path.splitext(pdf_file.name)[0]
                        prefix = base_name.split('_')[0] if '_' in base_name else base_name
                        stamp_rect = fitz.Rect(sx, sy, sx + ss, sy + ss)
                        for page_num, page in enumerate(doc, start=1):
                            page.insert_image(stamp_rect, filename=stamp_path, keep_proportion=True, overlay=True)
                            text = f"{prefix}-{page_num}"
                            pw = page.rect.width
                            text_rect = fitz.Rect(pw - 200, 20, pw - 20, 50)
                            page.insert_textbox(text_rect, text, fontsize=fs, color=(1, 0, 0), align=fitz.TEXT_ALIGN_RIGHT)
                        results.append((pdf_file.name, doc.tobytes())); doc.close()
                    zip_buf = BytesIO()
                    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for fname, fbytes in results: zf.writestr(fname, fbytes)
                    zip_buf.seek(0)
                    st.success(f"✅ {len(results)}개 PDF 도장 완료")
                    st.download_button("📥 ZIP 다운로드", data=zip_buf, file_name="stamped_pdfs.zip", mime="application/zip", use_container_width=True)
        else:
            st.info("PDF 파일과 도장 이미지를 모두 업로드해주세요.")

    with tab3:
        st.subheader("전체 프로세스 (이름변경 + 도장)")
        st.markdown("PDF + 도장 업로드 → AFTER 편집 → 이름변경 + 도장/번호 → ZIP 다운로드")
        all_pdfs = st.file_uploader("PDF 파일 업로드", type=["pdf"], accept_multiple_files=True, key="all_pdfs")
        all_stamp = st.file_uploader("도장 이미지", type=["png","jpg","jpeg"], key="all_stamp")
        if all_pdfs and all_stamp:
            names = [f.name for f in all_pdfs]
            df = pd.DataFrame({"BEFORE": names, "AFTER": names})
            st.markdown("**AFTER 열을 편집하세요:**")
            edited = st.data_editor(df, use_container_width=True, num_rows="fixed", key="all_editor")
            c1, c2, c3, c4 = st.columns(4)
            sx = c1.number_input("도장 X", value=0, step=10, key="asx")
            sy = c2.number_input("도장 Y", value=0, step=10, key="asy")
            ss = c3.number_input("도장 크기", value=100, step=10, key="ass")
            fs = c4.number_input("텍스트 크기", value=14, step=1, key="afs")
            if st.button("전체 실행 (이름변경 + 도장)", type="primary", use_container_width=True, key="all_run"):
                stamp_bytes = all_stamp.read()
                with tempfile.TemporaryDirectory() as tmp:
                    stamp_path = os.path.join(tmp, "stamp.png")
                    with open(stamp_path, "wb") as f: f.write(stamp_bytes)
                    results = []
                    for i, pdf_file in enumerate(all_pdfs):
                        new_name = str(edited.iloc[i]["AFTER"]).strip()
                        if not new_name.lower().endswith(".pdf"): new_name += ".pdf"
                        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
                        base_name = os.path.splitext(new_name)[0]
                        prefix = base_name.split('_')[0] if '_' in base_name else base_name
                        stamp_rect = fitz.Rect(sx, sy, sx + ss, sy + ss)
                        for page_num, page in enumerate(doc, start=1):
                            page.insert_image(stamp_rect, filename=stamp_path, keep_proportion=True, overlay=True)
                            text = f"{prefix}-{page_num}"
                            pw = page.rect.width
                            text_rect = fitz.Rect(pw - 200, 20, pw - 20, 50)
                            page.insert_textbox(text_rect, text, fontsize=fs, color=(1, 0, 0), align=fitz.TEXT_ALIGN_RIGHT)
                        results.append((new_name, doc.tobytes())); doc.close()
                    zip_buf = BytesIO()
                    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for fname, fbytes in results: zf.writestr(fname, fbytes)
                    zip_buf.seek(0)
                    st.success(f"✅ {len(results)}개 파일 처리 완료")
                    st.download_button("📥 ZIP 다운로드", data=zip_buf, file_name="processed_pdfs.zip", mime="application/zip", use_container_width=True)
        elif all_pdfs:
            st.info("도장 이미지도 업로드해주세요.")
        else:
            st.info("PDF 파일과 도장 이미지를 업로드하면 시작됩니다.")
