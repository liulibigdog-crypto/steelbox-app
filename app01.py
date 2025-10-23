# ---------------------- imports ----------------------
import math
import io
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

st.set_page_config(page_title="钢箱梁截面快速设计", page_icon="🧮", layout="wide")

# ---------------------- global CSS ----------------------
st.markdown("""
<style>
.main .block-container{
  max-width: 1320px;
  padding-top: 0.8rem;
  padding-bottom: 1.2rem;
}
[data-testid="stSidebar"]{
  width: 300px;
  min-width: 300px;
}
.card{
  background:#fff;
  border:1px solid #e9ecef;
  border-radius: 12px;
  padding: 14px 18px;
  box-shadow: 0 4px 12px rgba(0,0,0,.04);
  margin-bottom: 14px;
}
.card h4{ margin:0 0 .6rem 0; font-weight:600; }
.small{ color:#6c757d; font-size:.92rem; }
.figure-card{ display:flex; align-items:center; justify-content:center; }
h1, h2, h3 { margin-bottom:.4rem; }
</style>
""", unsafe_allow_html=True)

# ---------------------- drawing function (define FIRST!) ----------------------
def draw_section_cad(
    B_deck,            # m   单幅桥面宽
    B_box_mm,          # mm  箱梁外宽
    H_mm,              # mm  梁高
    t_top, t_bot,      # mm  顶/底板厚度
    t_web,             # mm  腹板厚度
    Nc,                #     箱室数
    out_top, out_bot,  # mm  顶/底板外挑翼缘
    e_web              # mm  外侧腹板距箱边的内收量
):
    """CAD 画风的截面示意：等室宽、对称尺寸、标注 H 与 t_web"""
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=150)

    # 等室宽几何
    clear_w = B_box_mm - 2 * e_web
    cell_w  = int(round(clear_w / Nc))           # 单室等宽（整数mm）
    x_webs  = [e_web + i * cell_w for i in range(1, Nc)]
    xL, xR  = e_web, B_box_mm - e_web

    # 顶部桥面总宽（对称尺寸）
    B_deck_mm = int(round(B_deck * 1000))
    oh = max(int(round((B_deck_mm - B_box_mm) / 2)), 0)

    # 外轮廓 & 顶/底板
    ax.add_patch(Rectangle((0, 0), B_box_mm, H_mm, fill=False, linewidth=1.2, edgecolor="#1a1a1a"))
    ax.add_patch(Rectangle((0, H_mm - t_top), B_box_mm, t_top, facecolor="#c7d7ef",
                           edgecolor="#1a1a1a", lw=1.0, alpha=0.35))
    ax.add_patch(Rectangle((0, 0),           B_box_mm, t_bot, facecolor="#c7d7ef",
                           edgecolor="#1a1a1a", lw=1.0, alpha=0.35))

    # 腹板（竖直）
    ax.plot([xL, xL], [t_bot, H_mm - t_top], color="#1a1a1a", lw=1.4)
    ax.plot([xR, xR], [t_bot, H_mm - t_top], color="#1a1a1a", lw=1.4)
    for x in x_webs:
        ax.plot([x, x], [t_bot, H_mm - t_top], color="#1a1a1a", lw=1.4)

    # 尺寸辅助
    def dim_h(ax, x0, x1, y, txt, off=38, arrows=True):
        ax.plot([x0, x1], [y, y], color="#1a1a1a", lw=1.0)
        if txt:
            ax.text((x0 + x1) / 2, y + off, txt, ha="center", va="bottom", fontsize=9)
        if arrows:
            s = 22
            ax.plot([x0, x0 + s], [y, y + s * 0.5], color="#1a1a1a", lw=1.0)
            ax.plot([x0, x0 + s], [y, y - s * 0.5], color="#1a1a1a", lw=1.0)
            ax.plot([x1, x1 - s], [y, y + s * 0.5], color="#1a1a1a", lw=1.0)
            ax.plot([x1, x1 - s], [y, y - s * 0.5], color="#1a1a1a", lw=1.0)

    def dim_v(ax, x, y0, y1, txt, off=42, arrows=True):
        ax.plot([x, x], [y0, y1], color="#1a1a1a", lw=1.0)
        if txt:
            ax.text(x - off, (y0 + y1) / 2, txt, ha="center", va="center", rotation=90, fontsize=9)
        if arrows:
            s = 22
            ax.plot([x, x - s * 0.5], [y0, y0 + s], color="#1a1a1a", lw=1.0)
            ax.plot([x, x + s * 0.5], [y0, y0 + s], color="#1a1a1a", lw=1.0)
            ax.plot([x, x - s * 0.5], [y1, y1 - s], color="#1a1a1a", lw=1.0)
            ax.plot([x, x + s * 0.5], [y1, y1 - s], color="#1a1a1a", lw=1.0)

    # 顶部：B_deck（对称）
    y_top = H_mm + 70
    ax.text(B_box_mm/2, y_top + 45, f"B_deck = {B_deck_mm} mm", ha="center", va="bottom", fontsize=10)
    dim_h(ax, 0 - oh, B_box_mm + oh, y_top, "", off=0, arrows=False)
    dim_h(ax, 0 - oh, 0, y_top, f"{oh}", off=0)
    x0 = 0
    for _ in range(Nc):
        x1 = x0 + cell_w
        dim_h(ax, x0, x1, y_top, f"{cell_w}", off=0)
        x0 = x1
    dim_h(ax, B_box_mm, B_box_mm + oh, y_top, f"{oh}", off=0)

    # 底部：B_box（对称）
    y_bot = -60
    ax.text(B_box_mm/2, y_bot - 45, f"B_box  = {B_box_mm:.0f} mm", ha="center", va="top", fontsize=10)
    dim_h(ax, 0, B_box_mm, y_bot, "", off=0, arrows=False)
    dim_h(ax, 0, out_bot, y_bot, f"{int(out_bot)}", off=0)
    x0 = out_bot
    for _ in range(Nc):
        x1 = x0 + cell_w
        dim_h(ax, x0, x1, y_bot, f"{cell_w}", off=0)
        x0 = x1
    dim_h(ax, B_box_mm - out_bot, B_box_mm, y_bot, f"{int(out_bot)}", off=0)

    # 梁高与厚度文字
    dim_v(ax, -80, 0, H_mm, f"H = {int(H_mm)} mm", off=34)
    ax.text(e_web * 0.4, H_mm - t_top / 2, f"t_top={int(t_top)} mm", va="center", fontsize=9, color="#1a1a1a")
    ax.text(e_web * 0.4, t_bot / 2,          f"t_bot={int(t_bot)} mm", va="center", fontsize=9, color="#1a1a1a")
    ax.text(B_box_mm / 2, y_bot + 20, f"t_web={int(t_web)} mm  (×{Nc+1} webs)", ha="center", va="bottom", fontsize=9)

    ax.set_aspect("equal")
    ax.set_xlim(-oh - 120, B_box_mm + oh + 120)
    ax.set_ylim(y_bot - 80, H_mm + 140)
    ax.axis("off")
    return fig

# ---------------------- title ----------------------
st.title("钢箱梁截面快速设计小工具")
st.caption("Made by **Lichen Liu** | 既有桥梁改造中钢箱梁截面快速初选与可视化展示（教学/方案比选）")

# ---------------------- sidebar inputs ----------------------
with st.sidebar:
    st.header("输入参数")

    # 内力（kN·m / kN）
    M_pos = st.number_input("跨中正弯矩 M+ (kN·m)", value=15400.0, step=100.0)
    M_neg = st.number_input("支点负弯矩 M- (kN·m)", value=32200.0, step=100.0)
    V     = st.number_input("支点最大剪力 V (kN)",   value=5360.0, step=50.0)

    st.markdown("---")
    # 几何（m）
    B_deck = st.number_input("单幅桥面总宽 B (m)", value=13.5, step=0.1, min_value=4.0)
    H      = st.number_input("梁高 H (m)",        value=2.0,  step=0.1, min_value=0.6)

    # 外宽控制
    st.subheader("桥面—箱梁横向关系")
    mode = st.radio("外宽控制方式", ("按左右预留带扣减", "按比例控制"), index=0)
    if mode == "按左右预留带扣减":
        L_res = st.number_input("左侧预留带 L_res (m)", value=1.00, step=0.1, min_value=0.0)
        R_res = st.number_input("右侧预留带 R_res (m)", value=1.00, step=0.1, min_value=0.0)
        B_box = B_deck - L_res - R_res
    else:
        box_ratio = st.slider("箱梁外宽/单幅桥面宽 α", 0.55, 0.90, 0.70, 0.01)
        B_box = box_ratio * B_deck

    st.markdown("---")
    # 材料
    fy      = st.number_input("钢材屈服强度 fy (MPa)", value=345.0, step=5.0)
    gamma0  = st.number_input("重要性系数 γ0", value=1.1, step=0.05)
    eta_beff= st.slider("翼缘有效宽折减 η (0.30–0.40)", 0.30, 0.40, 0.35, 0.01)

    # 翼缘与外侧腹板
    st.markdown("---")
    st.subheader("翼缘与外侧腹板（工程画法）")
    e_web   = st.number_input("外侧腹板距边缘内收 e_web (mm)", value=60.0,  step=5.0, min_value=0.0)
    out_top = st.number_input("顶板外伸翼缘 out_top (mm)",     value=145.0, step=5.0, min_value=0.0)
    out_bot = st.number_input("底板外伸翼缘 out_bot (mm)",     value=60.0,  step=5.0, min_value=0.0)

    st.caption("说明：以上为初选参数，结果用于方案阶段；定型需按规范进行强度、稳定、构造与疲劳验算。")

# ---------------------- calculations ----------------------
if B_box <= 0:
    st.error("❌ 箱梁外宽 B_box ≤ 0，请检查桥面与预留带/比例设置。")
    st.stop()

fd = fy / gamma0
M_pos_Nmm = M_pos * 1e6
M_neg_Nmm = M_neg * 1e6
Wreq_pos  = M_pos_Nmm / fd
Wreq_neg  = M_neg_Nmm / fd

beff      = eta_beff * (0.85 * B_box)   # m
B_box_mm  = B_box * 1000
beff_mm   = beff   * 1000
H_mm      = H      * 1000

t_bot_th = Wreq_pos / (H_mm * beff_mm)   # mm
t_top_th = Wreq_neg / (H_mm * beff_mm)   # mm

# 推荐箱室数
target_cell_w = 3.0
Nc_guess = max(1, min(4, int(round(B_box/target_cell_w))))
Nc = st.sidebar.selectbox("推荐单箱箱室数（可改）", [1,2,3,4], index=Nc_guess-1)
n_webs = Nc + 1

# 腹板理论厚度（考虑多腹板分担）
tau_allow = 0.58 * fy
h_w = 0.9 * H_mm
t_web_th = (V * 1e3) / (tau_allow * h_w * n_webs)

# 工程取值策略
t_corr        = st.sidebar.number_input("腐蚀/制造裕量 t_corr (mm)", value=2.0, step=1.0, min_value=0.0)
t_top_min     = st.sidebar.number_input("顶板构造下限 (mm)", value=16.0, step=1.0)
t_bot_min     = st.sidebar.number_input("底板构造下限 (mm)", value=14.0, step=1.0)
t_web_min_cons= st.sidebar.number_input("腹板构造下限 (mm)", value=12.0, step=1.0)
round_step    = st.sidebar.selectbox("厚度取整步长", [1, 2], index=1)

def round_up(x, step=2):
    return math.ceil(x / step) * step

t_top = round_up(max(t_top_th, t_top_min) + t_corr, round_step)
t_bot = round_up(max(t_bot_th, t_bot_min) + t_corr, round_step)
t_web = round_up(max(t_web_th, t_web_min_cons) + t_corr, round_step)

# ---------------------- layout & output ----------------------
left, right = st.columns([0.60, 0.40], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 计算结果（工程可用截面）")
    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("箱梁外宽 B_box", f"{B_box_mm:.0f} mm")
    mcol2.metric("箱室数 Nc", f"{Nc} 室")
    mcol3.metric("腹板厚 t_web", f"{int(t_web)} mm × {n_webs}")

    st.markdown(f"""
- 单幅桥面宽 **B_deck** = {B_deck:.2f} m；箱梁外宽 **B_box** = {B_box:.2f} m（占比 {B_box/B_deck*100:.1f}%）
- 所需模量：**Wreq+** = {Wreq_pos/1e6:.2f} ×10⁶ mm³，**Wreq-** = {Wreq_neg/1e6:.2f} ×10⁶ mm³
- 采用厚度：顶板 **t_top = {int(t_top)} mm**，底板 **t_bot = {int(t_bot)} mm**，腹板 **t_web = {int(t_web)} mm/片 × {n_webs}**  
- 外侧腹板内收 **e_web = {int(e_web)} mm**；翼缘：**out_top = {int(out_top)} mm**，**out_bot = {int(out_bot)} mm**
<p class="small">说明：已计入构造下限与腐蚀/制造裕量，并按 2 mm 进位；用于方案/初设直接采用。定型阶段仍需做局部稳定、剪切屈曲、宽厚比与疲劳等规范校核。</p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card figure-card">', unsafe_allow_html=True)
    st.subheader("推荐截面示意（工程画法）")
    fig = draw_section_cad(
        B_deck=B_deck,
        B_box_mm=B_box_mm,
        H_mm=H_mm,
        t_top=t_top,
        t_bot=t_bot,
        t_web=t_web,
        Nc=Nc,
        out_top=out_top,
        out_bot=out_bot,
        e_web=e_web
    )
    st.pyplot(fig, clear_figure=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card" style="text-align:center">', unsafe_allow_html=True)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=200)
    st.download_button("下载示意图 PNG", data=buf.getvalue(),
                       file_name="steel_box_section.png", mime="image/png",
                       use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("© 2025 Lichen Liu | 仅用于教学与方案比选。")
