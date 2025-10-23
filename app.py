# -*- coding: utf-8 -*-
import io
import math
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon

# =============== 页面 & 全局样式 ===============
st.set_page_config(page_title="钢箱梁截面快速设计", page_icon="🧮", layout="wide")

st.markdown("""
<style>
/* 主内容容器：居中、加宽、减小上下留白 */
.main .block-container{
  max-width: 1320px;
  padding-top: .6rem;
  padding-bottom: 1.0rem;
}
/* 侧边栏更紧凑 */
[data-testid="stSidebar"]{
  width: 300px;
  min-width: 300px;
}
/* 卡片：圆角+轻阴影+细边框 */
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
/* 默认标题下的空隙稍微压缩一点 */
h1,h2,h3{ margin-bottom:.45rem; }
</style>
""", unsafe_allow_html=True)

# =============== 绘图函数（先定义，再调用） ===============
DIM_CLR = "#1a1a1a"

def draw_section_cad(
    B_deck, B_box_mm, H_mm,
    t_top, t_bot, t_web, Nc,
    out_top, out_bot, e_web,
    dim_gap=120        # 尺寸整体外移距离（mm）
):
    """二维工程图（CAD风格）"""
    fig, ax = plt.subplots(figsize=(10.0, 5.2), dpi=150)

    # 等室宽（整数mm）
    clear_w = B_box_mm - 2*e_web
    cell_w  = int(round(clear_w / Nc))
    x_webs  = [e_web + i*cell_w for i in range(1, Nc)]
    xL, xR  = e_web, B_box_mm - e_web

    # 顶部桥面总宽（对称）
    B_deck_mm = int(round(B_deck * 1000))
    oh = max(int(round((B_deck_mm - B_box_mm)/2)), 0)

    # 外轮廓 & 顶/底板着色
    ax.add_patch(Rectangle((0, 0), B_box_mm, H_mm, fill=False,
                           linewidth=1.2, edgecolor=DIM_CLR))
    ax.add_patch(Rectangle((0, H_mm - t_top), B_box_mm, t_top,
                           facecolor="#c7d7ef", edgecolor=DIM_CLR, lw=1.0, alpha=0.35))
    ax.add_patch(Rectangle((0, 0), B_box_mm, t_bot,
                           facecolor="#c7d7ef", edgecolor=DIM_CLR, lw=1.0, alpha=0.35))

    # 腹板（竖直）
    for x in [xL, xR] + x_webs:
        ax.plot([x, x], [t_bot, H_mm - t_top], color=DIM_CLR, lw=1.4)

    # 尺寸辅助函数（水平/竖直）
    def dim_h(x0, x1, y, txt, off=34, arrows=True):
        ax.plot([x0, x1], [y, y], color=DIM_CLR, lw=1.0)
        if arrows:
            s = 22
            ax.plot([x0, x0+s], [y, y+s*0.5], color=DIM_CLR, lw=1.0)
            ax.plot([x0, x0+s], [y, y-s*0.5], color=DIM_CLR, lw=1.0)
            ax.plot([x1, x1-s], [y, y+s*0.5], color=DIM_CLR, lw=1.0)
            ax.plot([x1, x1-s], [y, y-s*0.5], color=DIM_CLR, lw=1.0)
        if txt:
            ax.text((x0+x1)/2, y+off, txt, ha="center", va="bottom", fontsize=9)

    def dim_v(x, y0, y1, txt, off=36, arrows=True):
        ax.plot([x, x], [y0, y1], color=DIM_CLR, lw=1.0)
        if arrows:
            s = 22
            ax.plot([x, x - s*0.5], [y0, y0 + s], color=DIM_CLR, lw=1.0)
            ax.plot([x, x + s*0.5], [y0, y0 + s], color=DIM_CLR, lw=1.0)
            ax.plot([x, x - s*0.5], [y1, y1 - s], color=DIM_CLR, lw=1.0)
            ax.plot([x, x + s*0.5], [y1, y1 - s], color=DIM_CLR, lw=1.0)
        if txt:
            ax.text(x - off, (y0+y1)/2, txt, ha="center", va="center", rotation=90, fontsize=9)

    # 顶部：B_deck（整体上移 dim_gap）
    y_top = H_mm + dim_gap
    ax.text(B_box_mm/2, y_top + 45, f"B_deck = {B_deck_mm} mm",
            ha="center", va="bottom", fontsize=10)
    dim_h(0 - oh, B_box_mm + oh, y_top, "", off=0, arrows=False)
    dim_h(0 - oh, 0, y_top, f"{oh}", off=0)
    x0 = 0
    for _ in range(Nc):
        x1 = x0 + cell_w
        dim_h(x0, x1, y_top, f"{cell_w}", off=0)
        x0 = x1
    dim_h(B_box_mm, B_box_mm + oh, y_top, f"{oh}", off=0)

    # 底部：B_box（整体下移 dim_gap）
    y_bot = -dim_gap
    ax.text(B_box_mm/2, y_bot - 45, f"B_box = {B_box_mm:.0f} mm",
            ha="center", va="top", fontsize=10)
    dim_h(0, B_box_mm, y_bot, "", off=0, arrows=False)
    dim_h(0, out_bot, y_bot, f"{int(out_bot)}", off=0)
    x0 = out_bot
    for _ in range(Nc):
        x1 = x0 + cell_w
        dim_h(x0, x1, y_bot, f"{cell_w}", off=0)
        x0 = x1
    dim_h(B_box_mm - out_bot, B_box_mm, y_bot, f"{int(out_bot)}", off=0)

    # 左侧：H（整体左移 dim_gap）
    dim_v(-dim_gap, 0, H_mm, f"H = {int(H_mm)} mm", off=34)

    # 厚度文字
    ax.text(e_web * 0.4, H_mm - t_top/2, f"t_top={int(t_top)} mm", va="center", fontsize=9, color=DIM_CLR)
    ax.text(e_web * 0.4, t_bot/2,        f"t_bot={int(t_bot)} mm", va="center", fontsize=9, color=DIM_CLR)
    ax.text(B_box_mm/2, y_bot + 20,      f"t_web={int(t_web)} mm  (×{Nc+1} webs)",
            ha="center", va="bottom", fontsize=9)

    ax.set_aspect("equal")
    ax.set_xlim(-oh - dim_gap*1.2 - out_top, B_box_mm + oh + dim_gap*1.2 + out_top)
    ax.set_ylim(y_bot - 80, y_top + 140)
    ax.axis("off")
    return fig


def draw_section_3d(
    B_deck, B_box_mm, H_mm,
    t_top, t_bot, t_web, Nc,
    out_top, out_bot, e_web,
    L_seg_mm=1500, dim_gap=120
):
    """简易“伪3D”立体示意（短梁段），论文配图友好"""
    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=150)

    # 透视偏移
    dx = 0.30 * L_seg_mm
    dy = 0.18 * L_seg_mm

    # 等室宽（整数mm）
    clear_w = B_box_mm - 2*e_web
    cell_w  = int(round(clear_w / Nc))
    x_webs  = [e_web + i*cell_w for i in range(1, Nc)]
    xL, xR  = e_web, B_box_mm - e_web

    # 顶部桥面总宽
    B_deck_mm = int(round(B_deck * 1000))
    oh = max(int(round((B_deck_mm - B_box_mm)/2)), 0)

    # 前后外框
    front = [(0,0), (B_box_mm,0), (B_box_mm,H_mm), (0,H_mm)]
    back  = [(x+dx, y+dy) for (x,y) in front]
    # 连接线
    for (x0,y0),(x1,y1) in zip(front, back):
        ax.plot([x0,x1], [y0,y1], color=DIM_CLR, lw=1.0)
    ax.add_patch(Polygon(front, closed=True, fill=False, edgecolor=DIM_CLR, lw=1.2))
    ax.add_patch(Polygon(back,  closed=True, fill=False, edgecolor=DIM_CLR, lw=1.0))

    # 顶/底板（含翼缘，前后各一）
    topF = [(-out_top, H_mm-t_top), (B_box_mm+out_top, H_mm-t_top),
            (B_box_mm+out_top, H_mm), (-out_top, H_mm)]
    topB = [(x+dx, y+dy) for (x,y) in topF]
    botF = [(-out_bot, 0), (B_box_mm+out_bot, 0),
            (B_box_mm+out_bot, t_bot), (-out_bot, t_bot)]
    botB = [(x+dx, y+dy) for (x,y) in botF]
    ax.add_patch(Polygon(topB, closed=True, facecolor="#dbe8ff", edgecolor=DIM_CLR, lw=0.8, alpha=0.55))
    ax.add_patch(Polygon(topF, closed=True, facecolor="#c7d7ef",  edgecolor=DIM_CLR, lw=1.0, alpha=0.65))
    ax.add_patch(Polygon(botB, closed=True, facecolor="#dbe8ff", edgecolor=DIM_CLR, lw=0.8, alpha=0.55))
    ax.add_patch(Polygon(botF, closed=True, facecolor="#c7d7ef",  edgecolor=DIM_CLR, lw=1.0, alpha=0.65))

    # 腹板（前后+连线）
    def draw_web(x):
        ax.plot([x, x], [t_bot, H_mm-t_top], color=DIM_CLR, lw=1.2)
        ax.plot([x+dx, x+dx], [t_bot+dy, H_mm-t_top+dy], color=DIM_CLR, lw=1.0)
        ax.plot([x, x+dx],   [t_bot, t_bot+dy],           color=DIM_CLR, lw=0.9)
        ax.plot([x, x+dx],   [H_mm-t_top, H_mm-t_top+dy], color=DIM_CLR, lw=0.9)
    for x in [xL, xR] + x_webs:
        draw_web(x)

    # 尺寸线（整体外移）
    def dim_h(x0, x1, y, txt):
        ax.plot([x0, x1], [y, y], color=DIM_CLR, lw=1.0)
        s = 22
        ax.plot([x0, x0+s], [y, y+s*0.5], color=DIM_CLR, lw=1.0)
        ax.plot([x0, x0+s], [y, y-s*0.5], color=DIM_CLR, lw=1.0)
        ax.plot([x1, x1-s], [y, y+s*0.5], color=DIM_CLR, lw=1.0)
        ax.plot([x1, x1-s], [y, y-s*0.5], color=DIM_CLR, lw=1.0)
        ax.text((x0+x1)/2, y+28, txt, ha="center", va="bottom", fontsize=9)

    def dim_v(x, y0, y1, txt):
        ax.plot([x, x], [y0, y1], color=DIM_CLR, lw=1.0)
        s = 22
        ax.plot([x, x - s*0.5], [y0, y0 + s], color=DIM_CLR, lw=1.0)
        ax.plot([x, x + s*0.5], [y0, y0 + s], color=DIM_CLR, lw=1.0)
        ax.plot([x, x - s*0.5], [y1, y1 - s], color=DIM_CLR, lw=1.0)
        ax.plot([x, x + s*0.5], [y1, y1 - s], color=DIM_CLR, lw=1.0)
        ax.text(x - 34, (y0+y1)/2, txt, ha="center", va="center", rotation=90, fontsize=9)

    # 上：B_deck（对称）
    y_top = H_mm + dim_gap
    dim_h(0 - oh, B_box_mm + oh, y_top, "")
    dim_h(0 - oh, 0, y_top, f"{oh}")
    x0 = 0
    clear_w = B_box_mm - 2*e_web
    cell_w  = int(round(clear_w / Nc))
    for _ in range(Nc):
        x1 = x0 + cell_w
        dim_h(x0, x1, y_top, f"{cell_w}")
        x0 = x1
    dim_h(B_box_mm, B_box_mm + oh, y_top, f"{oh}")
    ax.text(B_box_mm/2, y_top + 45, f"B_deck = {B_deck_mm} mm", ha="center", va="bottom", fontsize=10)

    # 下：B_box
    y_bot = -dim_gap
    dim_h(0, B_box_mm, y_bot, "")
    dim_h(0, out_bot, y_bot, f"{int(out_bot)}")
    x0 = out_bot
    for _ in range(Nc):
        x1 = x0 + cell_w
        dim_h(x0, x1, y_bot, f"{cell_w}")
        x0 = x1
    dim_h(B_box_mm - out_bot, B_box_mm, y_bot, f"{int(out_bot)}")
    ax.text(B_box_mm/2, y_bot - 45, f"B_box = {B_box_mm:.0f} mm", ha="center", va="top", fontsize=10)

    # 左：H
    dim_v(-dim_gap, 0, H_mm, f"H = {int(H_mm)} mm")

    # 厚度说明
    ax.text(e_web*0.4, H_mm - t_top/2, f"t_top={int(t_top)} mm",  va="center", fontsize=9, color=DIM_CLR)
    ax.text(e_web*0.4, t_bot/2,        f"t_bot={int(t_bot)} mm",  va="center", fontsize=9, color=DIM_CLR)
    ax.text(B_box_mm/2, y_bot + 20,    f"t_web={int(t_web)} mm (×{Nc+1} webs)",
            ha="center", va="bottom", fontsize=9)

    ax.set_aspect("equal")
    ax.set_xlim(-oh - dim_gap*1.3 - out_top, B_box_mm + dx + oh + dim_gap*1.1 + out_top)
    ax.set_ylim(y_bot - 120, H_mm + dy + dim_gap + 160)
    ax.axis("off")
    return fig

# =============== 标题 ===============
st.title("钢箱梁截面快速设计小工具")
st.caption("Made by **Lichen Liu**｜既有桥梁改造中钢箱梁截面快速初选与可视化展示（教学/方案比选）")

# =============== 侧边栏输入 ===============
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

    st.markdown("---")
    st.subheader("翼缘与外侧腹板（工程画法）")
    e_web   = st.number_input("外侧腹板距边缘内收 e_web (mm)", value=60.0,  step=5.0, min_value=0.0)
    out_top = st.number_input("顶板外伸翼缘 out_top (mm)",     value=145.0, step=5.0, min_value=0.0)
    out_bot = st.number_input("底板外伸翼缘 out_bot (mm)",     value=60.0,  step=5.0, min_value=0.0)

    st.markdown("---")
    st.subheader("示意图设置")
    view_mode = st.radio("示意图样式", ["二维工程图", "立体示意"], index=1, horizontal=True)
    L_seg     = st.number_input("示意梁段长度 L (m)", value=1.5, step=0.1, min_value=0.5, max_value=6.0)
    dim_gap   = st.number_input("标注距离（mm）", value=120, step=10, min_value=40, max_value=400)

    st.caption("说明：以上为初选参数，结果用于方案阶段；定型需按规范进行强度、稳定、构造与疲劳验算。")

# =============== 计算（工程可用截面） ===============
if B_box <= 0:
    st.error("❌ 箱梁外宽 B_box ≤ 0，请检查桥面与预留带/比例设置。")
    st.stop()

# 设计强度与所需模量
fd = fy / gamma0
M_pos_Nmm = M_pos * 1e6
M_neg_Nmm = M_neg * 1e6
Wreq_pos  = M_pos_Nmm / fd          # mm³
Wreq_neg  = M_neg_Nmm / fd          # mm³

# 有效宽度与几何
beff      = eta_beff * (0.85 * B_box)  # m
B_box_mm  = B_box * 1000
beff_mm   = beff   * 1000
H_mm      = H      * 1000

# 板厚理论值（用于内部）
t_bot_th = Wreq_pos / (H_mm * beff_mm)
t_top_th = Wreq_neg / (H_mm * beff_mm)

# 推荐箱室数（先定 Nc）
target_cell_w = 3.0  # m
Nc_guess = max(1, min(4, int(round(B_box/target_cell_w))))
Nc = st.sidebar.selectbox("推荐单箱箱室数（可改）", [1,2,3,4], index=Nc_guess-1)
n_webs = Nc + 1

# 腹板理论厚（剪力分担）
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

# =============== 结果 + 图 ===============
left, right = st.columns([0.55, 0.45], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 计算结果（工程可用截面）")

    m1, m2, m3 = st.columns(3)
    m1.metric("箱梁外宽 B_box", f"{B_box_mm:.0f} mm")
    m2.metric("箱室数 Nc", f"{Nc} 室")
    m3.metric("腹板厚 t_web", f"{int(t_web)} mm × {n_webs}")

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
    tabs = st.tabs(["二维工程图", "立体示意"])
    with tabs[0]:
        fig2d = draw_section_cad(
            B_deck=B_deck, B_box_mm=B_box_mm, H_mm=H_mm,
            t_top=t_top, t_bot=t_bot, t_web=t_web, Nc=Nc,
            out_top=out_top, out_bot=out_bot, e_web=e_web,
            dim_gap=dim_gap
        )
        st.pyplot(fig2d, clear_figure=True)
    with tabs[1]:
        fig3d = draw_section_3d(
            B_deck=B_deck, B_box_mm=B_box_mm, H_mm=H_mm,
            t_top=t_top, t_bot=t_bot, t_web=t_web, Nc=Nc,
            out_top=out_top, out_bot=out_bot, e_web=e_web,
            L_seg_mm=int(L_seg*1000), dim_gap=dim_gap
        )
        st.pyplot(fig3d, clear_figure=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 下载：根据当前选择视图导出
    st.markdown('<div class="card" style="text-align:center">', unsafe_allow_html=True)
    buf = io.BytesIO()
    (fig3d if view_mode == "立体示意" else fig2d).savefig(buf, format="png", bbox_inches="tight", dpi=200)
    st.download_button("下载示意图 PNG", data=buf.getvalue(),
                       file_name="steel_box_section.png", mime="image/png",
                       use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("© 2025 Lichen Liu | 仅用于教学与方案比选。")
