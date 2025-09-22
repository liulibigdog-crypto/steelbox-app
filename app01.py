# 自定义CSS样式
st.markdown("""
    <style>
    /* 页面整体居中 */
    .block-container {
        max-width: 850px;  /* 内容宽度 */
        margin: auto;      /* 居中 */
        padding-top: 2rem;
        padding-bottom: 2rem;
        background-color: white;
        border-radius: 12px;
        box-shadow: 0px 0px 15px rgba(0,0,0,0.08);
    }
    /* 页面背景与水印 */
    body {
        background: #f7f9fb;
        background-image: url("https://via.placeholder.com/400x400.png?text=Lichen+Liu");
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center;
        background-size: 50%;
        opacity: 0.98;
    }
    /* 让水印淡化 */
    body::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255,255,255,0.7);
        z-index: -1;
    }
    </style>
    """, unsafe_allow_html=True)

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

    st.markdown("---")
    st.caption("说明：以上为初选参数，结果仅用于方案阶段；定型需按规范进行强度、稳定、构造与疲劳等详尽验算。")

# ====== 计算核心 ======
# 单位换算
fd = fy / gamma0                       # 设计强度 (MPa = N/mm2)
M_pos_Nmm = M_pos * 1e6                # kN·m -> N·mm
M_neg_Nmm = M_neg * 1e6

# 所需截面模量（mm3）
Wreq_pos = M_pos_Nmm / fd
Wreq_neg = M_neg_Nmm / fd

# 有效宽度与箱宽的经验取值（可在主梁-桥面关系不明确时用于初选）
# 经验：单箱宽约占车行桥面宽的 0.65~0.80；这里取 0.70，可人工调整为控件
B_box = 0.70 * B_deck                  # m，箱体外宽（经验）
beff = eta_beff * (0.85 * B_box)       # m，折算有效宽度（0.85: 外伸+安全折减，工程经验）
# 转 mm
B_box_mm = B_box * 1000
beff_mm = beff * 1000
H_mm = H * 1000

# 顶/底板厚度：控制侧法（Hf≈H）
t_bot = Wreq_pos / (H_mm * beff_mm)    # mm
t_top = Wreq_neg / (H_mm * beff_mm)    # mm

# 腹板厚度：按 V ≤ 0.58 fy * t_w * h_w 求最小（初选），h_w ~ H_mm - 顶底板厚折减（这里近似用 H_mm）
tau_allow = 0.58 * fy                  # MPa
t_web_min = V * 1e3 / (tau_allow * H_mm)  # kN -> N；mm
t_web = max(t_web_min, 12.0)           # 不小于12mm的构造下限（可调）

# ====== 自动推荐单箱“几室” ======
# 经验规则（供初选）：
# - 单箱宽度 B_box（m）下，合适“单室宽”建议 2.5～3.5 m；
# - 推荐箱室数 Nc 使得每室宽 w_cell 接近 3.0 m；限制 1~4。
target_cell_w = 3.0
Nc_guess = max(1, min(4, int(round(B_box / target_cell_w))))
# 提示可手动覆盖
Nc = st.sidebar.selectbox("推荐单箱箱室数（可手动修改）", options=[1, 2, 3, 4], index=Nc_guess-1,
                          help="按 B_box≈0.7B 和每室 2.5–3.5m 初选；定型需结合扭转、施工与横隔布置综合确定。")

# 总腹板数 = 外腹板2 + 内腹板(Nc-1)
n_webs = Nc + 1

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
    st.info("提示：以上为方案阶段的快速初选值；定型应按规范对抗弯/抗剪、剪切屈曲、宽厚比、焊缝与横隔/加劲构造等进行校核。")

# ====== 截面示意图（可下载） ======
def draw_section(B_box_mm, H_mm, t_top, t_bot, t_web, Nc):
    """绘制简化的单箱多室截面示意（非严格比例，仅用于展示）"""
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)

    # 外轮廓（用顶/底板厚度近似）
    x0, y0 = 0, 0
    ax.add_patch(Rectangle((x0, y0), B_box_mm, H_mm, fill=False, linewidth=1.5))

    # 顶/底板示意（加粗显示）
    ax.add_patch(Rectangle((x0, H_mm - t_top), B_box_mm, t_top, fill=True, alpha=0.15))
    ax.add_patch(Rectangle((x0, 0), B_box_mm, t_bot, fill=True, alpha=0.15))

    # 腹板（等分布置）
    # 全宽分成 (Nc) 个室 => 需要 (Nc+1) 条腹板；最外侧两条在边缘
    # 这里按均布画 Nc-1 根内部腹板
    if Nc >= 2:
        spacing = B_box_mm / Nc
        for i in range(1, Nc):
            x = i * spacing
            ax.add_line(plt.Line2D([x, x], [t_bot, H_mm - t_top], linewidth=1.2))

    # 尺寸标注（简化）
    ax.text(B_box_mm/2, H_mm + 0.035*H_mm, f"B_box ≈ {B_box_mm/1000:.2f} m", ha="center", va="bottom")
    ax.text(-0.03*B_box_mm, H_mm/2, f"H = {H_mm/1000:.2f} m", ha="right", va="center", rotation=90)
    ax.text(B_box_mm*0.02, H_mm - t_top/2, f"t_top≈{t_top:.0f} mm", va="center")
    ax.text(B_box_mm*0.02, t_bot/2, f"t_bot≈{t_bot:.0f} mm", va="center")

    ax.set_aspect('equal')
    ax.set_xlim(-0.1*B_box_mm, 1.1*B_box_mm)
    ax.set_ylim(-0.1*H_mm, 1.15*H_mm)
    ax.axis('off')
    return fig

with col2:
    st.subheader("推荐截面示意（非比例，仅供展示）")
    fig = draw_section(B_box_mm, H_mm, t_top, t_bot, t_web, Nc)
    st.pyplot(fig, clear_figure=True)

    # 导出PNG
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    st.download_button("下载示意图 PNG", data=buf.getvalue(),
                       file_name="steel_box_section.png", mime="image/png")

# ====== 附加说明 ======
with st.expander("自动推荐箱室数的规则说明（点击展开）"):
    st.markdown(
        """
- **经验：** 单箱外宽通常占单幅桥面宽的 **0.65–0.80**；本工具默认 **0.70·B** 初选。  
- **箱室数 Nc**：按“**每室宽约 2.5–3.5 m**”原则，取使每室宽接近 3.0 m 的整数，并限制在 **1–4 室**；  
  该建议同时兼顾经济性、扭转刚度与施工可行性（最终仍需结合横隔布置与扭转验算进行调整）。
- **注意：** 本图仅为简化示意；定型需在 CAD/BIM 或有限元中落实详细尺寸与构造。
        """
    )

st.caption("© 2025 Lichen Liu | 仅用于教学与方案比选。")

