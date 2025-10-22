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
from matplotlib.patches import Rectangle, Wedge

def _dim_chain(ax, xs, y, up=True, color="k", fs=8):
    """
    在 y=常数 处画尺寸链：xs 为从左到右的分界 x 坐标列表
    在每段中点标注长度（mm），并画短“刻度线”
    """
    sign = +1 if up else -1
    tick = 0.012 * (xs[-1] - xs[0])          # 刻度高度相对总宽的 1.2%
    off  = 0.02  * (xs[-1] - xs[0])          # 文字离板面的偏移

    # 刻度线
    for x in xs:
        ax.plot([x, x], [y, y + sign*tick], color=color, lw=0.7)

    # 数值
    for i in range(len(xs)-1):
        x0, x1 = xs[i], xs[i+1]
        c  = 0.5*(x0+x1)
        L  = x1 - x0
        ax.text(c, y + sign*(tick + off),
                f"{L:.0f}", ha="center",
                va="bottom" if up else "top",
                fontsize=fs, color=color)

def draw_section(B_box_mm, H_mm, t_top, t_bot, t_web, Nc, out_top_mm, out_bot_mm):
    """
    工程画法的单箱多室截面：
    - 顶/底板为整幅薄板；
    - 外侧腹板：左 (x_topL=out_top, x_botL=out_bot)，右对称；
    - 内腹板：按 Nc 等分，连接 top/bot 的对应位置（可带斜度）；
    - 顶/底板外伸翼缘高亮并分别做尺寸链。
    """
    fig, ax = plt.subplots(figsize=(9.2, 3.8), dpi=150)

    y_top = H_mm - t_top
    y_bot = t_bot

    # 1) 顶/底板（整幅）
    ax.add_patch(Rectangle((0, y_top), B_box_mm, t_top, color="#1f77b4", alpha=0.20, lw=0.8))
    ax.add_patch(Rectangle((0, 0),     B_box_mm, t_bot, color="#1f77b4", alpha=0.20, lw=0.8))

    # 2) 外侧腹板顶/底坐标（允许 top/bot 外伸不同 => 腹板有角度）
    x_topL = out_top_mm
    x_topR = B_box_mm - out_top_mm
    x_botL = out_bot_mm
    x_botR = B_box_mm - out_bot_mm

    # 3) 高亮翼缘（外伸区）
    ax.add_patch(Rectangle((0, y_top),               x_topL, t_top, color="#1f77b4", alpha=0.35, lw=0))
    ax.add_patch(Rectangle((x_topR, y_top), B_box_mm-x_topR, t_top, color="#1f77b4", alpha=0.35, lw=0))
    ax.add_patch(Rectangle((0, 0),                  x_botL, t_bot, color="#1f77b4", alpha=0.35, lw=0))
    ax.add_patch(Rectangle((x_botR, 0),   B_box_mm - x_botR, t_bot, color="#1f77b4", alpha=0.35, lw=0))

    # 4) 外侧腹板（斜线）
    ax.plot([x_topL, x_botL], [y_top, y_bot], color="k", lw=1.2)
    ax.plot([x_topR, x_botR], [y_top, y_bot], color="k", lw=1.2)

    # 5) 内腹板：在 top 与 bot 间做线性插值，连成斜线（总体与外侧腹板同倾向）
    clear_top = x_topR - x_topL
    clear_bot = x_botR - x_botL
    if Nc >= 2:
        for i in range(1, Nc):
            r = i / Nc
            xt = x_topL + r * clear_top
            xb = x_botL + r * clear_bot
            ax.plot([xt, xb], [y_top, y_bot], color="k", lw=1.0)

    # 6) 顶/底与腹板交角处做小圆角（仅示意）
    r_top = min(0.5*t_top, 40)
    r_bot = min(0.5*t_bot, 40)
    # 所有腹板的 top/bot 交点
    xs_top = [x_topL] + ([x_topL + i*clear_top/Nc for i in range(1, Nc)] if Nc >= 2 else []) + [x_topR]
    xs_bot = [x_botL] + ([x_botL + i*clear_bot/Nc for i in range(1, Nc)] if Nc >= 2 else []) + [x_botR]
    for xt in xs_top:
        ax.add_patch(Wedge(center=(xt, y_top), r=r_top, theta1=180, theta2=360,
                           width=r_top*0.55, fill=False, lw=0.8))
    for xb in xs_bot:
        ax.add_patch(Wedge(center=(xb, y_bot), r=r_bot, theta1=0, theta2=180,
                           width=r_bot*0.55, fill=False, lw=0.8))

    # 7) 顶/底板尺寸链（mm）
    # 顶板： [0, out_top] + Nc 个室顶板宽 + [out_top, B_box]
    top_bounds = [0, x_topL] + [x_topL + k*clear_top/Nc for k in range(1, Nc)] + [x_topR, B_box_mm]
    _dim_chain(ax, top_bounds, y_top + 0.10*H_mm, up=True,  color="k", fs=8)
    # 底板： [0, out_bot] + Nc 个室底板宽 + [out_bot, B_box]
    bot_bounds = [0, x_botL] + [x_botL + k*clear_bot/Nc for k in range(1, Nc)] + [x_botR, B_box_mm]
    _dim_chain(ax, bot_bounds, 0        - 0.12*H_mm, up=False, color="k", fs=8)

    # 8) 关键文字
    ax.text(B_box_mm/2, H_mm + 0.08*H_mm, f"B_box = {B_box_mm/1000:.2f} m", ha="center", va="bottom", fontsize=10)
    ax.text(-0.035*B_box_mm, H_mm/2, f"H = {H_mm/1000:.2f} m", ha="right", va="center", rotation=90, fontsize=10)
    ax.text(0.01*B_box_mm, y_top + 0.02*H_mm, f"t_top≈{t_top:.0f} mm", color="#1f77b4", fontsize=9)
    ax.text(0.01*B_box_mm, 0.02*H_mm,       f"t_bot≈{t_bot:.0f} mm", color="#1f77b4", fontsize=9)

    ax.set_aspect('equal')
    ax.set_xlim(-0.12*B_box_mm, 1.12*B_box_mm)
    ax.set_ylim(-0.20*H_mm,     1.22*H_mm)
    ax.axis('off')
    return fig

with col2:
    st.subheader("推荐截面示意（工程画法）")
    fig = draw_section(B_box_mm, H_mm, t_top, t_bot, t_web, Nc, out_top, out_bot)
    st.pyplot(fig, clear_figure=True)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    st.download_button("下载示意图 PNG", data=buf.getvalue(),
                       file_name="steel_box_section.png", mime="image/png")

st.caption("© 2025 Lichen Liu | 仅用于教学与方案比选。")

