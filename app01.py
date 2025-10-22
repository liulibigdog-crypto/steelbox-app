import math
import io
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

st.set_page_config(page_title="钢箱梁截面快速设计", page_icon="🧮", layout="wide")

# ====== 顶部标题 & 作者信息 ======
st.title("钢箱梁截面快速设计小工具")
st.caption("Made by **Lichen Liu** | 本工具用于既有桥梁改造中钢箱梁截面快速初选与可视化展示（教学/方案比选用）")

# ====== 侧边栏输入 ======
with st.sidebar:
    st.header("输入参数")
    # 内力（kN·m / kN）
    M_pos = st.number_input("跨中正弯矩 M+ (kN·m)", value=15400.0, step=100.0)
    M_neg = st.number_input("支点负弯矩 M- (kN·m)", value=32200.0, step=100.0)
    V = st.number_input("支点最大剪力 V (kN)", value=5360.0, step=50.0)

    st.markdown("---")
    # 几何（m）
    B_deck = st.number_input("单幅桥面总宽 B (m)", value=13.5, step=0.1, min_value=4.0)
    H = st.number_input("梁高 H (m)", value=2.0, step=0.1, min_value=0.6)

    st.markdown("---")
    # 材料（MPa）
    fy = st.number_input("钢材屈服强度 fy (MPa)", value=345.0, step=5.0)
    gamma0 = st.number_input("重要性系数 γ0", value=1.1, step=0.05)
    eta_beff = st.slider("翼缘有效宽度折减系数 η (0.30–0.40)", 0.30, 0.40, 0.35, 0.01)
# ====== 计算核心 ======
fd = fy / gamma0                        # 设计强度 (MPa = N/mm2)
M_pos_Nmm = M_pos * 1e6                 # kN·m -> N·mm
M_neg_Nmm = M_neg * 1e6

# 所需截面模量（mm3）
Wreq_pos = M_pos_Nmm / fd
Wreq_neg = M_neg_Nmm / fd

# ====== 用单幅桥面宽度控制箱梁总外宽 ======
with st.sidebar:
    st.markdown("---")
    st.subheader("桥面—箱梁横向关系")

    mode = st.radio(
        "选择外宽控制方式",
        ("按左右预留带扣减", "按百分比控制（箱梁外宽/单幅桥面宽）"),
        index=0,
        help="两种方式二选一。预留带包括护栏、防撞墙、检修带等不属于箱梁的横向带宽。"
    )

    if mode == "按左右预留带扣减":
        L_res = st.number_input("左侧预留带 L_res (m)", value=1.00, step=0.1, min_value=0.0)
        R_res = st.number_input("右侧预留带 R_res (m)", value=1.00, step=0.1, min_value=0.0)
        B_box = B_deck - L_res - R_res            # ← 用设计桥面宽直接控制箱梁外宽
    else:
        box_ratio = st.slider("箱梁外宽/单幅桥面宽  α", 0.55, 0.90, 0.70, 0.01)
        B_box = box_ratio * B_deck

# 合法性检查
if B_box <= 0.0:
    st.error("❌ 计算得到的箱梁外宽 B_box ≤ 0。请调整左右预留带或比例。")
    st.stop()
if B_box < 0.4 * B_deck:
    st.warning("⚠️ B_box 过小，相对桥面宽偏窄，请复核预留带/比例设置与结构受力。")

# 有效宽度（m）与换算（mm）
beff = eta_beff * (0.85 * B_box)        # 仍采用折减经验，可按需细化
B_box_mm = B_box * 1000
beff_mm = beff * 1000
H_mm = H * 1000

# 顶/底板厚度（mm）：控制侧法（Hf≈H）
t_bot = Wreq_pos / (H_mm * beff_mm)
t_top = Wreq_neg / (H_mm * beff_mm)

# 腹板厚度（mm）：V ≤ 0.58 fy t_w h_w
tau_allow = 0.58 * fy
t_web_min = V * 1e3 / (tau_allow * H_mm)
t_web = max(t_web_min, 12.0)

# ====== 翼缘外伸（新增） ======
# 默认取箱宽的 5% 作为单侧翼缘外伸
default_e = 0.05 * B_box_mm
with st.sidebar:
    st.markdown("---")
    st.subheader("翼缘外伸（用于显示翼缘宽度与侧腹板倾角）")
    e_top = st.number_input("顶板边缘翼缘外伸 e_top (mm)", value=float(f"{default_e:.0f}"), step=10.0, min_value=0.0)
    e_bot = st.number_input("底板边缘翼缘外伸 e_bot (mm)", value=float(f"{default_e:.0f}"), step=10.0, min_value=0.0)
    st.caption("说明：外侧腹板在翼缘内缘位置；若 e_top ≠ e_bot，外侧腹板将形成倾角。")

# ====== 自动推荐箱室数 ======
target_cell_w = 3.0
Nc_guess = max(1, min(4, int(round(B_box / target_cell_w))))
Nc = st.sidebar.selectbox("推荐单箱箱室数（可手动修改）", options=[1, 2, 3, 4], index=Nc_guess-1,
                          help="按 B_box≈0.7B 和每室 2.5–3.5m 初选；定型需结合扭转、施工与横隔布置综合确定。")

n_webs = Nc + 1  # 总腹板数（外腹板2 + 内腹板 Nc-1）

# ====== 结果区 ======
col1, col2 = st.columns([1.2, 1.0], gap="large")

with col1:
    st.subheader("计算结果（初选）")
    st.write(f"- 跨中所需截面模量 **Wreq+** = {Wreq_pos/1e6:.2f} ×10⁶ mm³")
    st.write(f"- 支点所需截面模量 **Wreq-** = {Wreq_neg/1e6:.2f} ×10⁶ mm³")
    st.write(f"- 经验箱体外宽 **B_box** ≈ {B_box:.2f} m（约为 B 的 70%）")
    st.write(f"- 推荐箱室数 **Nc** = {Nc}（总腹板数 {n_webs}）")
    st.write(f"- 顶板厚度 **t_top** ≈ {t_top:.1f} mm（负弯矩控制）")
    st.write(f"- 底板厚度 **t_bot** ≈ {t_bot:.1f} mm（正弯矩控制）")
    st.write(f"- 腹板厚度 **t_web** ≥ {t_web:.1f} mm（剪力初选）")
    st.write(f"- 顶/底单侧翼缘外伸 **e_top / e_bot** = {e_top:.0f} / {e_bot:.0f} mm")
    st.info("提示：以上为方案阶段快速初选；定型需按规范进行抗弯/抗剪、屈曲、宽厚比、焊缝与横隔/加劲构造详验算。")

# ====== 截面示意图（更新：显示翼缘宽度 & 侧腹板倾角） ======
def draw_section(B_box_mm, H_mm, t_top, t_bot, t_web, Nc, e_top_mm, e_bot_mm):
    """
    绘制单箱多室截面示意：
    - 顶/底板显示为整幅板；
    - 外侧腹板位于翼缘内缘（顶面 x=e_top, 底面 x=e_bot），因此会自然成角；
    - 内腹板顶/底位置分别按等分计算并连线（可出现轻微倾角）。
    """
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)

    # 1) 外轮廓（箱体外边界；仅示意）
    ax.add_patch(Rectangle((0, 0), B_box_mm, H_mm, fill=False, linewidth=1.5))

    # 2) 顶/底板（整幅显示）
    ax.add_patch(Rectangle((0, H_mm - t_top), B_box_mm, t_top, color="#1f77b4", alpha=0.18))
    ax.add_patch(Rectangle((0, 0), B_box_mm, t_bot, color="#1f77b4", alpha=0.18))

    # 3) 外侧腹板顶/底位置（决定倾角）
    x_top_L = e_top_mm
    x_top_R = B_box_mm - e_top_mm
    x_bot_L = e_bot_mm
    x_bot_R = B_box_mm - e_bot_mm

    # 4) 画外侧腹板（倾斜）
    ax.plot([x_top_L, x_bot_L], [H_mm - t_top, t_bot], color="k", linewidth=1.2)
    ax.plot([x_top_R, x_bot_R], [H_mm - t_top, t_bot], color="k", linewidth=1.2)

    # 5) 内腹板：顶/底等分并连线
    if Nc >= 2:
        span_top = x_top_R - x_top_L
        span_bot = x_bot_R - x_bot_L
        for i in range(1, Nc):  # 需要 Nc-1 根内腹板
            xt = x_top_L + i * span_top / Nc
            xb = x_bot_L + i * span_bot / Nc
            ax.plot([xt, xb], [H_mm - t_top, t_bot], color="k", linewidth=1.0)

    # 6) 尺寸与说明
    ax.text(B_box_mm/2, H_mm + 0.035*H_mm, f"B_box ≈ {B_box_mm/1000:.2f} m", ha="center", va="bottom")
    ax.text(-0.03*B_box_mm, H_mm/2, f"H = {H_mm/1000:.2f} m", ha="right", va="center", rotation=90)
    ax.text(B_box_mm*0.02, H_mm - t_top/2, f"t_top≈{t_top:.0f} mm", va="center", color="#1f77b4")
    ax.text(B_box_mm*0.02, t_bot/2,       f"t_bot≈{t_bot:.0f} mm", va="center", color="#1f77b4")

    # 翼缘外伸标注（单侧）
    ax.annotate(f"e_top={e_top_mm:.0f} mm", xy=(x_top_L, H_mm - t_top),
                xytext=(x_top_L - 0.08*B_box_mm, H_mm - 0.15*H_mm),
                arrowprops=dict(arrowstyle="->", lw=0.8), ha="right")
    ax.annotate(f"e_bot={e_bot_mm:.0f} mm", xy=(x_bot_L, t_bot),
                xytext=(x_bot_L - 0.08*B_box_mm, 0.12*H_mm),
                arrowprops=dict(arrowstyle="->", lw=0.8), ha="right")

    ax.set_aspect('equal')
    ax.set_xlim(-0.1*B_box_mm, 1.1*B_box_mm)
    ax.set_ylim(-0.1*H_mm, 1.15*H_mm)
    ax.axis('off')
    return fig

with col2:
    st.subheader("推荐截面示意（显示翼缘与侧腹板倾角）")
    fig = draw_section(B_box_mm, H_mm, t_top, t_bot, t_web, Nc, e_top, e_bot)
    st.pyplot(fig, clear_figure=True)

    # 导出PNG
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    st.download_button("下载示意图 PNG", data=buf.getvalue(),
                       file_name="steel_box_section.png", mime="image/png")

# ====== 附加说明 ======
with st.expander("自动推荐箱室数与翼缘外伸说明（点击展开）"):
    st.markdown(
        """
- **箱宽经验：** 单箱外宽通常占单幅桥面宽的 **0.65–0.80**（本工具默认以 **0.70·B** 初选）。  
- **箱室数 Nc：** 按“每室宽约 2.5–3.5 m”原则，取使每室宽接近 3.0 m 的整数（限制 1–4 室）。  
- **翼缘外伸 e_top / e_bot：** 表示顶/底板边缘翼缘超出外侧腹板的宽度；若 e_top ≠ e_bot，则外侧腹板形成 **倾角**。  
- **说明：** 本图为简化示意；定型需在 CAD/BIM 或有限元中落实详细尺寸与构造。
        """
    )

st.caption("© 2025 Lichen Liu | 仅用于教学与方案比选。")
