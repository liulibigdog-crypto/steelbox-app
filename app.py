import streamlit as st

st.title("钢箱梁截面快速设计小工具")

st.header("输入参数")
M_pos = st.number_input("跨中正弯矩 M+ (kN·m)", value=15400.0)
M_neg = st.number_input("支点负弯矩 M- (kN·m)", value=32200.0)
V = st.number_input("支点最大剪力 V (kN)", value=5360.0)
B = st.number_input("桥面宽度 B (m)", value=13.5)
H = st.number_input("梁高 H (m)", value=2.0)
fy = st.number_input("钢材屈服强度 fy (MPa)", value=345.0)
gamma0 = st.number_input("重要性系数 γ0", value=1.1)

# 单位换算
fd = fy / gamma0  # 设计强度 MPa = N/mm²
M_pos_Nmm = M_pos * 1e6  # kN·m → N·mm
M_neg_Nmm = M_neg * 1e6

# 计算所需截面模量
Wreq_pos = M_pos_Nmm / fd
Wreq_neg = M_neg_Nmm / fd

st.header("计算结果")
st.write(f"跨中所需截面模量 Wreq+ = {Wreq_pos/1e6:.2f} ×10^6 mm³")
st.write(f"支点所需截面模量 Wreq- = {Wreq_neg/1e6:.2f} ×10^6 mm³")

# 简单推荐厚度（经验公式）
beff = 0.35 * B * 1000  # 有效宽度，mm
t_bot = Wreq_pos / (H*1000 * beff)  # mm
t_top = Wreq_neg / (H*1000 * beff)  # mm
t_web = V*1e3 / (0.58*fy * H*1000)  # mm，近似腹板厚度

st.subheader("推荐截面尺寸（初步估算）")
st.write(f"顶板厚度 ≈ {t_top:.1f} mm")
st.write(f"底板厚度 ≈ {t_bot:.1f} mm")
st.write(f"腹板厚度 ≈ {t_web:.1f} mm")

st.info("注：本结果为初步估算，需结合规范进行局部屈曲和构造验算。")
