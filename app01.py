import math
import io
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Wedge

st.set_page_config(page_title="钢箱梁截面快速设计", page_icon="🧮", layout="wide")

# ====== 标题 ======
st.title("钢箱梁截面快速设计小工具")
st.caption("Made by **Lichen Liu** | 既有桥梁改造中钢箱梁截面快速初选与可视化展示（教学/方案比选）")

# ====== 侧边栏输入 ======
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

    # 用桥面宽控制箱梁外宽（给两种方式，任选其一）
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
    # 材料（MPa）
    fy      = st.number_input("钢材屈服强度 fy (MPa)", value=345.0, step=5.0)
    gamma0  = st.number_input("重要性系数 γ0", value=1.1, step=0.05)
    eta_beff= st.slider("翼缘有效宽折减 η (0.30–0.40)", 0.30, 0.40, 0.35, 0.01)

    # 翼缘与外侧腹板（工程画法）
    st.markdown("---")
    st.subheader("翼缘与外侧腹板（工程画法）")
    e_web   = st.number_input("外侧腹板距边缘内收 e_web (mm)", value=60.0,  step=5.0, min_value=0.0)
    out_top = st.number_input("顶板外伸翼缘 out_top (mm)",     value=145.0, step=5.0, min_value=0.0)
    out_bot = st.number_input("底板外伸翼缘 out_bot (mm)",     value=60.0,  step=5.0, min_value=0.0)

    st.caption("说明：以上为初选参数，结果用于方案阶段；定型需按规范进行强度、稳定、构造与疲劳验算。")

# ====== 计算 ======
if B_box <= 0:
    st.error("❌ 箱梁外宽 B_box ≤ 0，请检查桥面与预留带/比例设置。")
    st.stop()

fd = fy / gamma0
M_pos_Nmm = M_pos * 1e6
M_neg_Nmm = M_neg * 1e6
Wreq_pos  = M_pos_Nmm / fd
Wreq_neg  = M_neg_Nmm / fd

beff      = eta_beff * (0.85 * B_box)
B_box_mm  = B_box * 1000
beff_mm   = beff   * 1000
H_mm      = H      * 1000

t_bot = Wreq_pos / (H_mm * beff_mm)
t_top = Wreq_neg / (H_mm * beff_mm)

tau_allow = 0.58 * fy
t_web_min = V * 1e3 / (tau_allow * H_mm)
t_web     = max(t_web_min, 12.0)

# 推荐箱室数
target_cell_w = 3.0
Nc_guess = max(1, min(4, int(round(B_box/target_cell_w))))
Nc = st.sidebar.selectbox("推荐单箱箱室数（可改）", [1,2,3,4], index=Nc_guess-1)

# ====== 结果展示 ======
col1, col2 = st.columns([1.2, 1.0], gap="large")

with col1:
    st.subheader("计算结果（初选）")
    st.write(f"- 单幅桥面宽 **B_deck** = {B_deck:.2f} m；箱梁外宽 **B_box** = {B_box:.2f} m（占比 {B_box/B_deck*100:.1f}%）")
    st.write(f"- **Wreq+** = {Wreq_pos/1e6:.2f} ×10⁶ mm³；**Wreq-** = {Wreq_neg/1e6:.2f} ×10⁶ mm³")
    st.write(f"- 推荐 **Nc={Nc}**（总腹板数 {Nc+1}）")
    st.write(f"- **t_top≈{t_top:.1f} mm**, **t_bot≈{t_bot:.1f} mm**, **t_web≥{t_web:.1f} mm**")
    st.write(f"- 外侧腹板内收 **e_web={e_web:.0f} mm**；翼缘：**out_top={out_top:.0f} mm**, **out_bot={out_bot:.0f} mm**")
    st.info("提示：方案阶段结果；定型需进行抗弯/抗剪、屈曲、宽厚比、焊缝与横隔/加劲构造详验算。")

# ====== 画图（工程画法） ======
import numpy as np
from matplotlib.patches import Rectangle, Wedge, FancyArrowPatch

DIM_COLOR = "#444"

def _dim_arrow_h(ax, x0, x1, y_dim, y_from0, y_from1=None,
                 text="", above=True, color=DIM_COLOR, fs=8, ms=10):
    """
    CAD风格水平尺寸：两端引出线 + 双箭头尺寸线 + 中部文字
    x0, x1      : 被标注的两点x坐标（mm）
    y_dim       : 尺寸线y坐标（mm）
    y_from0/1   : 引出线起点（构件边缘的y），到y_dim画引出线
    above       : True文字在尺寸线上方；False在下方
    """
    if y_from1 is None:
        y_from1 = y_from0

    # 引出线
    ax.plot([x0, x0], [y_from0, y_dim], color=color, lw=0.8)
    ax.plot([x1, x1], [y_from1, y_dim], color=color, lw=0.8)

    # 尺寸线（双箭头）
    arr = FancyArrowPatch((x0, y_dim), (x1, y_dim),
                          arrowstyle="<->,head_width=4,head_length=6",
                          mutation_scale=ms, lw=0.9, color=color)
    ax.add_patch(arr)

    # 文字
    dy = 0.018 * (ax.get_ylim()[1] - ax.get_ylim()[0])
    ax.text((x0 + x1) / 2, y_dim + (dy if above else -dy),
            text, ha="center",
            va="bottom" if above else "top",
            fontsize=fs, color=color)


def _dim_chain_cad(ax, xs, y_dim, y_from, above=True, color=DIM_COLOR, fs=8, ms=10):
    """
    CAD风格连续尺寸：xs为从左到右的分界点序列
    每一段画引出线+双箭头+数值（mm）
    """
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        _dim_arrow_h(ax, x0, x1, y_dim, y_from, y_from,
                     text=f"{x1 - x0:.0f}", above=above, color=color, fs=fs, ms=ms)


def draw_section(B_box_mm, H_mm, t_top, t_bot, t_web, Nc, out_top_mm, out_bot_mm, B_deck_m):
    """
    CAD风格工程画法：
    - 顶部：B_deck 连续双箭头；底部：B_box 连续双箭头
    - 顶/底板分别做连续链式尺寸（翼缘段 + 箱室净宽段）
    - 所有腹板竖直
    """
    fig, ax = plt.subplots(figsize=(9.6, 4.2), dpi=150)

    y_top = H_mm - t_top
    y_bot = t_bot

    # 1) 顶/底板整幅
    ax.add_patch(Rectangle((0, y_top), B_box_mm, t_top, color="#1f77b4", alpha=0.20, lw=0.8))
    ax.add_patch(Rectangle((0, 0),     B_box_mm, t_bot, color="#1f77b4", alpha=0.20, lw=0.8))

    # 2) 外侧腹板（竖直）
    x_webL = out_top_mm
    x_webR = B_box_mm - out_top_mm
    ax.plot([x_webL, x_webL], [y_bot, y_top], color="black", lw=1.2)
    ax.plot([x_webR, x_webR], [y_bot, y_top], color="black", lw=1.2)

    # 3) 内腹板：竖直等分
    if Nc >= 2:
        clear = x_webR - x_webL
        cell_w = clear / Nc
        for i in range(1, Nc):
            xi = x_webL + i * cell_w
            ax.plot([xi, xi], [y_bot, y_top], color="black", lw=1.0)

    # 4) 高亮翼缘区（顶/底）
    ax.add_patch(Rectangle((0, y_top),               out_top_mm, t_top, color="#1f77b4", alpha=0.35, lw=0))
    ax.add_patch(Rectangle((x_webR, y_top), B_box_mm - x_webR, t_top, color="#1f77b4", alpha=0.35, lw=0))
    ax.add_patch(Rectangle((0, 0),                  out_bot_mm, t_bot, color="#1f77b4", alpha=0.35, lw=0))
    ax.add_patch(Rectangle((B_box_mm - out_bot_mm, 0), out_bot_mm, t_bot, color="#1f77b4", alpha=0.35, lw=0))

    # 5) 顶/底与腹板交角的小圆角（示意）
    r_top = min(0.5 * t_top, 40)
    r_bot = min(0.5 * t_bot, 40)
    xs_all = [x_webL] + ([x_webL + i * (x_webR - x_webL) / Nc for i in range(1, Nc)] if Nc >= 2 else []) + [x_webR]
    for x in xs_all:
        ax.add_patch(Wedge(center=(x, y_top), r=r_top, theta1=180, theta2=360, width=r_top * 0.55, fill=False, lw=0.8))
        ax.add_patch(Wedge(center=(x, y_bot), r=r_bot, theta1=0,   theta2=180, width=r_bot * 0.55, fill=False, lw=0.8))

    # 6) 顶/底板连续尺寸（翼缘 + 箱室净宽）
    # 顶：翼缘段
    top_dim_y = y_top + 0.16 * H_mm
    _dim_arrow_h(ax, 0, out_top_mm, top_dim_y, y_top, text=f"{out_top_mm:.0f}", above=True)
    # 顶：箱室净宽段
    xs_top = [x_webL] + [x_webL + k * (x_webR - x_webL) / Nc for k in range(1, Nc)] + [x_webR]
    _dim_chain_cad(ax, xs_top, top_dim_y, y_top, above=True)

    # 底：翼缘段
    bot_dim_y = 0 - 0.18 * H_mm
    _dim_arrow_h(ax, 0, out_bot_mm, bot_dim_y, 0, text=f"{out_bot_mm:.0f}", above=False)
    # 底：箱室净宽段
    _dim_chain_cad(ax, xs_top, bot_dim_y, 0, above=False)

    # 7) 总宽尺寸（顶：B_deck；底：B_box）
    # 顶部总宽（文本写 B_deck，几何跨的是箱宽 B_box）
    top_total_y = y_top + 0.28 * H_mm
    _dim_arrow_h(ax, 0, B_box_mm, top_total_y, y_top, text=f"B_deck = {B_deck_m:.2f} m", above=True, fs=9, ms=12)
    # 底部总宽
    bot_total_y = 0 - 0.30 * H_mm
    _dim_arrow_h(ax, 0, B_box_mm, bot_total_y, 0,     text=f"B_box  = {B_box_mm/1000:.2f} m", above=False, fs=9, ms=12)

    # 8) 板厚文字
    ax.text(0.012 * B_box_mm, y_top + 0.03 * H_mm, f"t_top≈{t_top:.0f} mm", color="#1f77b4", fontsize=9)
    ax.text(0.012 * B_box_mm, 0.03  * H_mm,       f"t_bot≈{t_bot:.0f} mm", color="#1f77b4", fontsize=9)

    ax.set_aspect('equal')
    ax.set_xlim(-0.14 * B_box_mm, 1.14 * B_box_mm)
    ax.set_ylim(-0.32 * H_mm,     1.32 * H_mm)
    ax.axis('off')
    return fig

with col2:
    st.subheader("推荐截面示意（工程画法）")
    fig = draw_section(B_box_mm, H_mm, t_top, t_bot, t_web, Nc, out_top, out_bot, B_deck)
    st.pyplot(fig, clear_figure=True)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    st.download_button("下载示意图 PNG", data=buf.getvalue(),
                       file_name="steel_box_section.png", mime="image/png")

st.caption("© 2025 Lichen Liu | 仅用于教学与方案比选。")


