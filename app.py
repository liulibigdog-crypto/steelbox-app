import io
import time
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

st.set_page_config(page_title="钢箱梁截面快速设计", page_icon="🧮", layout="wide")

# ====== 标题 & 作者 ======
st.title("钢箱梁截面快速设计小工具")
st.caption("Made by **Lichen Liu** ｜ 方案阶段快速初选（输入→计算→示意图/结果导出）")

# ====== 侧边栏输入 ======
with st.sidebar:
    st.header("输入参数")
    # 内力（kN·m / kN）
    M_pos = st.number_input("跨中正弯矩 M+ (kN·m)", value=15400.0, step=100.0, min_value=0.0)
    M_neg = st.number_input("支点负弯矩 M- (kN·m)", value=32200.0, step=100.0, min_value=0.0)
    V = st.number_input("支点最大剪力 V (kN)", value=5360.0, step=50.0, min_value=0.0)

    st.markdown("---")
    # 几何（m）
    B_deck = st.number_input("单幅桥面总宽 B (m)", value=13.5, step=0.1, min_value=4.0)
    H = st.number_input("梁高 H (m)", value=2.0, step=0.1, min_value=0.6)

    st.markdown("---")
    # 材料（MPa）
    fy = st.number_input("钢材屈服强度 fy (MPa)", value=345.0, step=5.0, min_value=100.0)
    gamma0 = st.number_input("重要性系数 γ0", value=1.1, step=0.05, min_value=1.0)
    eta_beff = st.slider("翼缘有效宽度折减系数 η (0.30–0.40)", 0.30, 0.40, 0.35, 0.01)
    st.markdown("---")
    st.caption("注：本工具用于方案阶段初选；定型需做强度、稳定、宽厚比、疲劳与构造等详验算。")

# ====== 计算按钮与进度条区 ======
run = st.button("🚀 开始计算")
progress_placeholder = st.empty()
status_placeholder = st.empty()
result_container = st.container()  # 结果区容器（便于刷新）

if run:
    # —— Step 1: 输入校核 ——
    progress = progress_placeholder.progress(0, text="正在检查输入参数…")
    time.sleep(0.2)

    ok = True
    msg = []
    if B_deck <= 0 or H <= 0:
        ok = False
        msg.append("几何尺寸（B 或 H）必须为正。")
    if fy <= 0 or gamma0 <= 0:
        ok = False
        msg.append("材料参数（fy、γ0）必须为正。")

    progress.progress(10, text="正在检查输入参数…")
    time.sleep(0.1)

    if not ok:
        status_placeholder.error("输入有误：" + "；".join(msg))
        progress_placeholder.empty()
    else:
        # —— Step 2: 单位与需求值 ——
        progress.progress(30, text="正在计算需求模量与剪力条件…")
        time.sleep(0.2)
        fd = fy / gamma0                         # 设计强度 (MPa = N/mm²)
        M_pos_Nmm = M_pos * 1e6                  # kN·m → N·mm
        M_neg_Nmm = M_neg * 1e6
        Wreq_pos = M_pos_Nmm / fd                # mm³
        Wreq_neg = M_neg_Nmm / fd

        # —— Step 3: 经验箱宽与有效宽度 ——
        progress.progress(50, text="正在估算箱体外宽与有效宽度…")
        time.sleep(0.2)
        B_box = 0.70 * B_deck                    # m，经验：单箱外宽≈0.65~0.80·B，取0.70·B
        beff = eta_beff * (0.85 * B_box)         # m，0.85为外伸与安全折减的经验项
        B_box_mm = B_box * 1000
        beff_mm = beff * 1000
        H_mm = H * 1000

        # —— Step 4: 翼缘厚度（控制侧法） ——
        progress.progress(65, text="正在反算顶/底板厚度（控制侧法）…")
        time.sleep(0.2)
        t_bot = Wreq_pos / (H_mm * beff_mm)      # mm（跨中正弯矩控制底板）
        t_top = Wreq_neg / (H_mm * beff_mm)      # mm（支点负弯矩控制顶板）

        # —— Step 5: 腹板厚度（剪力初选） ——
        progress.progress(80, text="正在计算腹板厚度（剪力约束）…")
        time.sleep(0.2)
        tau_allow = 0.58 * fy                    # MPa
        t_web_min = (V * 1e3) / (tau_allow * H_mm) if H_mm > 0 else 0.0
        t_web = max(t_web_min, 12.0)             # 构造下限 12mm

        # —— Step 6: 推荐箱室 ——
        progress.progress(90, text="正在推荐箱室数…")
        time.sleep(0.2)
        target_cell_w = 3.0                      # m
        Nc_guess = max(1, min(4, int(round(B_box / target_cell_w))))
        progress.progress(100, text="计算完成")

        # 清理进度提示
        time.sleep(0.1)
        progress_placeholder.empty()
        status_placeholder.success("计算完成 ✅")

        # ====== 输出结果与图 ======
        with result_container:
            left, right = st.columns([1.1, 1.2], gap="large")

            with left:
                st.subheader("计算结果（初选）")
                st.write(f"- 跨中所需模量 **Wreq+** = {Wreq_pos/1e6:.2f} ×10⁶ mm³")
                st.write(f"- 支点所需模量 **Wreq-** = {Wreq_neg/1e6:.2f} ×10⁶ mm³")
                st.write(f"- 经验箱体外宽 **B_box** ≈ {B_box:.2f} m（约为 B 的 70%）")

                Nc = st.selectbox("推荐单箱箱室数（可手动修改）", [1,2,3,4], index=Nc_guess-1,
                                  help="每室宽约 2.5–3.5 m；最终需结合扭转、横隔布置与施工确定。")
                n_webs = Nc + 1

                st.write(f"- 顶板厚度 **t_top** ≈ {t_top:.1f} mm（负弯矩控制）")
                st.write(f"- 底板厚度 **t_bot** ≈ {t_bot:.1f} mm（正弯矩控制）")
                st.write(f"- 腹板厚度 **t_web** ≥ {t_web:.1f} mm（剪力初选，构造下限 12 mm）")
                st.write(f"- 推荐箱室数 **Nc** = {Nc}（总腹板数 {n_webs}）")

                # 简单满足性提示
                Wact_bot = H_mm * beff_mm * t_bot
                Wact_top = H_mm * beff_mm * t_top
                ok_bot = Wact_bot >= Wreq_pos * 0.999
                ok_top = Wact_top >= Wreq_neg * 0.999
                if ok_bot and ok_top:
                    st.success("抗弯需求满足（控制侧法，Hf≈H，有效宽度法估算）。")
                else:
                    st.error("抗弯需求未满足，请增厚翼缘或调整梁高/有效宽度。")

                # 计算日志（可选）
                with st.expander("查看计算日志/公式"):
                    st.markdown(
                        f"""
- 设计强度：\( f_d = \\frac{{f_y}}{{\\gamma_0}} = {fy:.1f}/{gamma0:.2f} = {fy/gamma0:.1f}\ \) MPa  
- 所需模量：\( W_+ = M_+/f_d = {M_pos:.0f}\\times10^6 / {fy/gamma0:.1f} \)，
  \( W_- = M_-/f_d = {M_neg:.0f}\\times10^6 / {fy/gamma0:.1f} \)  
- 有效宽度：\( b_{{eff}} = \\eta\\cdot 0.85\\cdot B_{{box}} = {eta_beff:.2f}\\times0.85\\times{B_box:.2f} \) m  
- 翼缘厚度：\( t_{{bot}} = W_+/(H\\,b_{{eff}}) \)，\( t_{{top}} = W_-/(H\\,b_{{eff}}) \)  
- 腹板厚度：\( V \\le 0.58 f_y t_w H \\Rightarrow t_w \\ge {t_web_min:.1f}\ \)mm（构造下限取 {t_web:.1f} mm）
                        """
                    )

            with right:
                st.subheader("推荐截面示意（非比例，仅供展示）")

                def draw_section(B_box_mm, H_mm, t_top, t_bot, Nc):
                    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
                    # 外轮廓
                    ax.add_patch(Rectangle((0, 0), B_box_mm, H_mm, fill=False, linewidth=1.6))
                    # 顶/底板
                    ax.add_patch(Rectangle((0, H_mm - t_top), B_box_mm, t_top, fill=True, alpha=0.18))
                    ax.add_patch(Rectangle((0, 0), B_box_mm, t_bot, fill=True, alpha=0.18))
                    # 内腹板（等分）
                    if Nc >= 2:
                        spacing = B_box_mm / Nc
                        for i in range(1, Nc):
                            x = i * spacing
                            ax.add_line(plt.Line2D([x, x], [t_bot, H_mm - t_top], linewidth=1.2))
                    # 注释
                    ax.text(B_box_mm/2, H_mm + 0.035*H_mm, f"B_box ≈ {B_box_mm/1000:.2f} m", ha="center", va="bottom")
                    ax.text(-0.03*B_box_mm, H_mm/2, f"H = {H_mm/1000:.2f} m", ha="right", va="center", rotation=90)
                    ax.text(B_box_mm*0.02, H_mm - t_top/2, f"t_top≈{t_top:.0f} mm", va="center")
                    ax.text(B_box_mm*0.02, t_bot/2, f"t_bot≈{t_bot:.0f} mm", va="center")
                    ax.set_aspect('equal'); ax.set_xlim(-0.1*B_box_mm, 1.1*B_box_mm); ax.set_ylim(-0.1*H_mm, 1.15*H_mm)
                    ax.axis('off')
                    return fig

                fig = draw_section(B_box_mm, H_mm, t_top, t_bot, Nc)
                st.pyplot(fig, clear_figure=True)

                # 下载 PNG
                buf = io.BytesIO()
                fig.savefig(buf, format="png", bbox_inches="tight")
                st.download_button("下载示意图 PNG", data=buf.getvalue(),
                                   file_name="steel_box_section.png", mime="image/png")

# 页脚
st.caption("© 2025 Lichen Liu | 仅用于教学与方案比选。")
