import streamlit as st
import tempfile
import os
import subprocess
import random
import base64

st.set_page_config(page_title="MP4 to WebP 일괄 변환기 (랜덤 파일명)", page_icon="🖼️", layout="centered")

st.title("🖼️ 양의 WEBP 변환기")

# 설명 문구들 (폰트 크기 통일)
st.write("10000XXXXX 형태의 5자리 랜덤 파일명으로 도출되며 일괄 다운로드 혹은 개별 다운로드를 진행할 수 있습니다.")
st.write("여러 MP4 파일을 선택하면 일괄 변환하며 다운로드할 수 있습니다.")

# 세션 상태 초기화
if "converted_files" not in st.session_state:
    st.session_state.converted_files = []
if "download_trigger" not in st.session_state:
    st.session_state.download_trigger = False

# 파일 업로더 (라벨 숨김)
uploaded_files = st.file_uploader(
    "", 
    type=["mp4"], 
    accept_multiple_files=True,
    label_visibility="collapsed"
)

if uploaded_files:
    st.info(f"📁 총 {len(uploaded_files)}개의 파일이 선택되었습니다.")
    
    if st.button("🔄 WEBP로 전체 변환 시작", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        temp_dir = tempfile.mkdtemp()
        st.session_state.converted_files = []
        st.session_state.download_trigger = False

        # 5자리 랜덤 시작 번호 생성 (10000 ~ 99999)
        start_rand_num = random.randint(10000, 99999)

        for idx, uploaded_file in enumerate(uploaded_files):
            current_num = start_rand_num + idx
            
            if current_num > 99999:
                current_num = 10000 + (current_num - 100000)
                
            output_name = f"10000{current_num}.webp"

            status_text.text(f"⏳ [{idx + 1}/{len(uploaded_files)}] 변환 중: {uploaded_file.name} ➔ {output_name}")
            
            tmp_input_path = os.path.join(temp_dir, uploaded_file.name)
            with open(tmp_input_path, "wb") as f:
                f.write(uploaded_file.read())

            output_path = os.path.join(temp_dir, output_name)

            try:
                cmd = [
                    'ffmpeg',
                    '-y',
                    '-i', tmp_input_path,
                    '-vcodec', 'libwebp',
                    '-filter:v', 'fps=fps=min(source_fps\,30)',
                    '-lossless', '0',
                    '-q:v', '53',
                    '-preset', 'default',
                    '-loop', '0',
                    output_path
                ]
                
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    with open(output_path, "rb") as f:
                        file_bytes = f.read()
                    file_size_mb = round(len(file_bytes) / (1024 * 1024), 2)
                    
                    st.session_state.converted_files.append((output_name, uploaded_file.name, file_bytes, file_size_mb))

            except Exception as e:
                st.error(f"❌ {uploaded_file.name} 변환 실패: {e}")

            progress_bar.progress((idx + 1) / len(uploaded_files))

        status_text.empty()
        progress_bar.empty()

# 변환 결과 출력 (항상 유지)
if st.session_state.converted_files:
    st.success(f"🔮 총 {len(st.session_state.converted_files)}개 파일 변환 완료!")
    st.markdown("---")
    
    st.subheader("📦 전체 일괄 다운로드")
    
    if st.button("⚡ 변환된 WebP 전체 한 번에 다운로드", use_container_width=True, type="secondary"):
        st.session_state.download_trigger = True

    # -------------------------------------------------------------
    # [수정된 일괄 다운로드 로직] 
    # 0.3초 동시성 제거 -> 순차 async/await 루프 및 1.5초 텀 적용
    # -------------------------------------------------------------
    if st.session_state.download_trigger:
        js_code = """
        <script>
        async function downloadAllFiles() {
            const files = [
        """
        for output_name, _, file_bytes, _ in st.session_state.converted_files:
            b64 = base64.b64encode(file_bytes).decode()
            js_code += f"{{name: '{output_name}', b64: '{b64}'}},\n"
        
        js_code += """
            ];
            
            for (let i = 0; i < files.length; i++) {
                var a = document.createElement('a');
                a.href = 'data:image/webp;base64,' + files[i].b64;
                a.download = files[i].name;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                // 이전 파일이 기기에 안전하게 저장될 수 있도록 1.5초(1500ms) 대기 후 다음 파일 진행
                if (i < files.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 1500));
                }
            }
        }
        downloadAllFiles();
        </script>
        """
        st.components.v1.html(js_code, height=1, width=1)
        st.session_state.download_trigger = False  # 실행 후 트리거 리셋

    st.markdown("---")
    st.subheader("📥 개별 다운로드 목록")

    for idx, (output_name, orig_name, file_bytes, file_size_mb) in enumerate(st.session_state.converted_files):
        st.write(f"**{idx + 1}. {output_name}** (원본: `{orig_name}` / {file_size_mb} MB)")
        st.download_button(
            label=f"📥 {output_name} 다운로드",
            data=file_bytes,
            file_name=output_name,
            mime="image/webp",
            key=f"rand_download_{idx}_{output_name}",
            use_container_width=True
        )
