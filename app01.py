import math
import io
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

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

# ====== 计算（工程可用截面） ======
if B_box <= 0:
    st.error("❌ 箱梁外宽 B_box ≤ 0，请检查桥面与预留带/比例设置。")
    st.stop()

# 设计强度与所需模量
fd = fy / gamma0
M_pos_Nmm = M_pos * 1e6
M_neg_Nmm = M_neg * 1e6
Wreq_pos  = M_pos_Nmm / fd   # mm^3（正弯矩控制底板）
Wreq_neg  = M_neg_Nmm / fd   # mm^3（负弯矩控制顶板）

# 有效宽度与几何
beff      = eta_beff * (0.85 * B_box)   # m
B_box_mm  = B_box * 1000
beff_mm   = beff   * 1000
H_mm      = H      * 1000

# 板厚“理论值”（仅用于内部计算，不展示）
t_bot_th = Wreq_pos / (H_mm * beff_mm)   # mm
t_top_th = Wreq_neg / (H_mm * beff_mm)   # mm

# —— 推荐箱室数 ——（先确定 Nc，便于腹板剪力分担）
target_cell_w = 3.0
Nc_guess = max(1, min(4, int(round(B_box/target_cell_w))))
Nc = st.sidebar.selectbox("推荐单箱箱室数（可改）", [1,2,3,4], index=Nc_guess-1)
n_webs = Nc + 1                            # 总腹板片数（外侧两片 + 内腹板）

# 腹板“理论值”（剪力），考虑多腹板分担
tau_allow = 0.58 * fy
h_w = 0.9 * H_mm   # 取腹板计算高度约为 0.9H，可按 H_mm - t_top_th - t_bot_th
t_web_th = (V * 1e3) / (tau_allow * h_w * n_webs)  # mm/片

# —— 工程取值策略（默认更贴近工程） ——
t_corr        = st.sidebar.number_input("腐蚀/制造裕量 t_corr (mm)", value=2.0, step=1.0, min_value=0.0)
t_top_min     = st.sidebar.number_input("顶板构造下限 (mm)", value=16.0, step=1.0)
t_bot_min     = st.sidebar.number_input("底板构造下限 (mm)", value=14.0, step=1.0)
t_web_min_cons= st.sidebar.number_input("腹板构造下限 (mm)", value=12.0, step=1.0)
round_step    = st.sidebar.selectbox("厚度取整步长", [1, 2], index=1)  # 常用 2mm 进位

def round_up(x, step=2):
    return math.ceil(x / step) * step

# —— 采用值（取大 + 裕量 + 进位） ——
t_top = round_up(max(t_top_th, t_top_min) + t_corr, round_step)  # 顶板（负弯矩）
t_bot = round_up(max(t_bot_th, t_bot_min) + t_corr, round_step)  # 底板（正弯矩）
t_web = round_up(max(t_web_th, t_web_min_cons) + t_corr, round_step)  # 每片腹板

# ====== 结果展示（工程可用） ======
col1, col2 = st.columns([1.2, 1.0], gap="large")

with col1:
    st.subheader("计算结果（工程可用截面）")
    st.write(
        f"- 单幅桥面宽 **B_deck** = {B_deck:.2f} m；箱梁外宽 **B_box** = {B_box:.2f} m "
        f"（占比 {B_box/B_deck*100:.1f}%）"
    )
    st.write(
        f"- 所需模量：**Wreq+** = {Wreq_pos/1e6:.2f} ×10⁶ mm³，**Wreq-** = {Wreq_neg/1e6:.2f} ×10⁶ mm³"
    )
    st.write(f"- 推荐箱室数 **Nc = {Nc}**（总腹板数 {n_webs}）")
    st.write(
        f"- 采用厚度：顶板 **t_top = {int(t_top)} mm**，底板 **t_bot = {int(t_bot)} mm**，"
        f"腹板 **t_web = {int(t_web)} mm/片** × {n_webs} 片"
    )
    st.write(
        f"- 外侧腹板内收 **e_web = {e_web:.0f} mm**；翼缘：**out_top = {out_top:.0f} mm**，"
        f"**out_bot = {out_bot:.0f} mm**"
    )
    st.caption("说明：已计入构造下限与腐蚀/制造裕量，并按 2 mm 进位；用于方案/初设直接采用。定型阶段仍需做局部稳定、剪切屈曲、宽厚比与疲劳等规范校核。")

# ====== 画图（工程画法 / CAD风格） ======
DIM_CLR = "#333"   # 尺寸线颜色

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
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=150)

    # ===== 1) 等室宽几何（整数 mm，最后一室吸收误差） =====
    clear_w = B_box_mm - 2 * e_web
    cell_w  = int(round(clear_w / Nc))
    # 内腹板位置
    x_webs = []
    x_run = e_web
    for i in range(1, Nc):
        x_run += cell_w
        x_webs.append(x_run)
    # 强制右侧外腹板位置
    xL = e_web
    xR = B_box_mm - e_web

    # ===== 2) 顶部桥面总宽（对称） =====
    B_deck_mm = int(round(B_deck * 1000))
    oh = max(int(round((B_deck_mm - B_box_mm) / 2)), 0)

    # ===== 3) 结构边界与板 =====
    ax.add_patch(Rectangle((0, 0), B_box_mm, H_mm, fill=False, linewidth=1.2, edgecolor="#1a1a1a"))
    ax.add_patch(Rectangle((0, H_mm - t_top), B_box_mm, t_top, facecolor="#c7d7ef", edgecolor="#1a1a1a", lw=1.0, alpha=0.35))
    ax.add_patch(Rectangle((0, 0),           B_box_mm, t_bot, facecolor="#c7d7ef", edgecolor="#1a1a1a", lw=1.0, alpha=0.35))

    # 腹板（竖直）
    ax.plot([xL, xL], [t_bot, H_mm - t_top], color="#1a1a1a", lw=1.4)
    ax.plot([xR, xR], [t_bot, H_mm - t_top], color="#1a1a1a", lw=1.4)
    for x in x_webs:
        ax.plot([x, x], [t_bot, H_mm - t_top], color="#1a1a1a", lw=1.4)

    # ===== 4) 尺寸标注工具 =====
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

    # ===== 5) 顶部：B_deck 尺寸链（对称，先oh，再等室宽，再oh） =====
    y_top = H_mm + 70
    ax.text(B_box_mm/2, y_top + 45, f"B_deck = {B_deck_mm} mm", ha="center", va="bottom", fontsize=10)
    # 总链（无箭头）
    dim_h(ax, -oh, B_box_mm + oh, y_top, "", off=0, arrows=False)
    # 左/右余量
    dim_h(ax, -oh, 0, y_top, f"{oh}", off=0)
    dim_h(ax, B_box_mm, B_box_mm + oh, y_top, f"{oh}", off=0)
    # 内部等室宽（从 e_web 开始，到 B_box_mm - e_web 结束；最后一段吸收误差）
    x0 = e_web
    for i in range(Nc):
        x1 = (B_box_mm - e_web) if i == Nc - 1 else (x0 + cell_w)
        seg = int(round(x1 - x0))
        dim_h(ax, x0, x1, y_top, f"{seg}", off=0)
        x0 = x1

    # ===== 6) 底部：B_box 尺寸链（对称，先翼缘，再等室宽，再翼缘） =====
    y_bot = -60
    ax.text(B_box_mm/2, y_bot - 45, f"B_box  = {B_box_mm:.0f} mm", ha="center", va="top", fontsize=10)
    dim_h(ax, 0, B_box_mm, y_bot, "", off=0, arrows=False)
    # 左翼缘
    dim_h(ax, 0, out_bot, y_bot, f"{int(out_bot)}", off=0)
    # 中间箱室
    x0 = out_bot
    for i in range(Nc):
        x1 = (B_box_mm - out_bot) if i == Nc - 1 else (x0 + cell_w)
        seg = int(round(x1 - x0))
        dim_h(ax, x0, x1, y_bot, f"{seg}", off=0)
        x0 = x1
    # 右翼缘
    dim_h(ax, B_box_mm - out_bot, B_box_mm, y_bot, f"{int(out_bot)}", off=0)

    # ===== 7) 梁高与厚度说明 =====
    dim_v(ax, -80, 0, H_mm, f"H = {int(H_mm)} mm", off=34)
    ax.text(e_web * 0.4, H_mm - t_top / 2, f"t_top={int(t_top)} mm", va="center", fontsize=9, color="#1a1a1a")
    ax.text(e_web * 0.4, t_bot / 2,          f"t_bot={int(t_bot)} mm", va="center", fontsize=9, color="#1a1a1a")
    ax.text(B_box_mm / 2, y_bot + 20, f"t_web={int(t_web)} mm  (×{Nc+1} webs)", ha="center", va="bottom", fontsize=9)

    ax.set_aspect("equal")
    ax.set_xlim(-oh - 120, B_box_mm + oh + 120)
    ax.set_ylim(y_bot - 80, H_mm + 140)
    ax.axis("off")
    return fig

with col2:
    st.subheader("推荐截面示意（工程画法）")
    # ✅ 调用新函数，传入 e_web
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

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    st.download_button("下载示意图 PNG", data=buf.getvalue(),
                       file_name="steel_box_section.png", mime="image/png")

st.caption("© 2025 Lichen Liu | 仅用于教学与方案比选。")
