import base64
import math
import os
import subprocess
import time
import cadquery as cq
import streamlit as st
from PIL import Image

hor_tolerance = 0.8
vert_tolerance = 0.8
chamfer_multi = 1


def cut_image(h, res, height):
    chamfer = h['h_break'] * chamfer_multi
    cut_im = (
        cq.Workplane('XY')
        .box(h['h_break'], h['h_break_len'], height, centered=(1, 1, 0))
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    chamfer_top = (
        cq.Workplane('XY')
        .box(chamfer, h['h_break_len'], chamfer)
        .rotate([0, 0, 0], [0, 1, 0], 45)
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    chamfer_bot = (
        cq.Workplane('XY')
        .box(chamfer, h['h_break_len'], chamfer)
        .rotate([0, 0, 0], [0, 1, 0], 45)
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], height])
    )
    return res - cut_im - chamfer_top - chamfer_bot


def normal_hinge(h, res, height):
    chamfer = h['h_break'] * chamfer_multi
    pin_diam = (h['h_diam'] - vert_tolerance) / 3
    x_hinge = -h['h_break'] / 2 - pin_diam / 2
    res = cut_image(h, res, height)

    hole_h_im_x = (h['h_diam'] + pin_diam) / 2 + hor_tolerance
    hole_im = (
        cq.Workplane('XY')
        .box(hole_h_im_x, h['h_thick'] + hor_tolerance * 2, height, centered=(1, 1, 0))
        .translate([-hole_h_im_x / 2 - h['h_break'] / 2, 0, 0])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    res -= hole_im

    hole_diam = pin_diam + vert_tolerance
    hinge_corn = (
        cq.Workplane('XZ')
        .box(hole_h_im_x / 2 + chamfer * math.sqrt(2), h['h_diam'], h['h_thick'], centered=(0, 0, 1))
        .translate([-h['h_break'] / 2 - pin_diam / 2, 0, height / 2 - h['h_diam'] / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hinge_ext = (
        cq.Workplane('XZ')
        .cylinder(h['h_thick'], h['h_diam'] / 2, centered=(1, 0, 1))
        .translate([x_hinge, 0, height / 2 - h['h_diam'] / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hinge_hole = (
        cq.Workplane('XZ')
        .cylinder(h['h_thick'], hole_diam / 2, centered=(1, 0, 1))
        .translate([x_hinge, 0, height / 2 - hole_diam / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hinge_pin = (
        cq.Workplane('XZ')
        .cylinder(h['h_thick'] + hor_tolerance * 2, pin_diam / 2, centered=(1, 0, 1))
        .translate([x_hinge, 0, height / 2 - pin_diam / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    return res + hinge_corn + hinge_ext - hinge_hole + hinge_pin


def ball_joint(h, res, height):
    res = cut_image(h, res, height)
    hole_diam = h['h_diam'] + vert_tolerance

    hole_im1 = (
        cq.Workplane('XY')
        .sphere(hole_diam / 2)
        .translate([-h['h_break'] / 2 - hole_diam / 2, 0, height / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hole_im2 = (
        cq.Workplane('XY')
        .sphere(hole_diam / 2)
        .translate([+h['h_break'] / 2 + hole_diam / 2, 0, height / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    if h.get('h_expose', True):
        hole_join = (
            cq.Workplane('XY')
            .box(h['h_break'] + (h['h_diam'] / 2 + hor_tolerance) * 2, h['h_diam'] / 2 + hor_tolerance, height, centered=(1, 1, 0))
            .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
            .translate([h['h_tran'][0], h['h_tran'][1], 0])
        )
    else:
        hole_join = (
            cq.Workplane('YZ')
            .cylinder(h['h_break'] + h['h_diam'], h['h_diam'] / 4 + hor_tolerance)
            .translate([0, 0, height / 2])
            .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
            .translate([h['h_tran'][0], h['h_tran'][1], 0])
        )
    res -= hole_im1 + hole_im2 + hole_join

    ball1 = (
        cq.Workplane('XY')
        .sphere(h['h_diam'] / 2)
        .translate([-h['h_break'] / 2 - hole_diam / 2, 0, height / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    ball2 = (
        cq.Workplane('XY')
        .sphere(h['h_diam'] / 2)
        .translate([+h['h_break'] / 2 + hole_diam / 2, 0, height / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    join = (
        cq.Workplane('YZ')
        .cylinder(h['h_break'] + h['h_diam'], h['h_diam'] / 4)
        .translate([0, 0, height / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    return res + ball1 + ball2 + join


st.set_page_config(layout="wide")

if 'height_val' not in st.session_state:
    st.session_state['height_val'] = 8.0
if 'hinge_list' not in st.session_state:
    st.session_state['hinge_list'] = [
        {'x': -25.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'},
        {'x': 0.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'},
        {'x': 25.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'}
    ]
if 'cur_h_idx' not in st.session_state:
    st.session_state['cur_h_idx'] = 0

# Боковая панель для общих настроек
with st.sidebar:
    st.title("⚙️ Настройки")
    filetype = st.selectbox("Формат файла", ["jpg", "png", "jpeg", "svg"])
    out_format = st.selectbox("Формат сохранения", ["stl", "step"])
    uploaded_file = st.file_uploader("Загрузите файл", type=[filetype])

    st.write(f"**Толщина детали:** {st.session_state['height_val']:.1f} мм")
    hb1, hb2 = st.columns(2)
    with hb1:
        if st.button("➖ Тоньше"):
            st.session_state['height_val'] = max(2.0, st.session_state['height_val'] - 1.0)
            st.rerun()
    with hb2:
        if st.button("➕ Толще"):
            st.session_state['height_val'] = min(50.0, st.session_state['height_val'] + 1.0)
            st.rerun()

if uploaded_file is not None:
    raw_path = f"file.{filetype}"
    with open(raw_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    if filetype == "png":
        subprocess.run(f"convert {raw_path} -background white -alpha remove -alpha off {raw_path}", shell=True)
    if filetype != "svg":
        subprocess.run(f"convert {raw_path} file.pnm", shell=True)
        subprocess.run("potrace -s -o file.svg file.pnm", shell=True)
    else:
        subprocess.run(f"cp {raw_path} file.svg", shell=True)

    if os.path.exists("file.dxf"):
        os.remove("file.dxf")

    with open("svg_to_dxf.scad", "w") as f:
        f.write('scale([0.4, 0.4, 1]) import(file = "file.svg", center = true);')
    subprocess.run("openscad svg_to_dxf.scad -o file.dxf", shell=True)

    base_model = cq.importers.importDXF("file.dxf").wires().toPending().extrude(st.session_state['height_val'])
    bbox = base_model.combine().objects[0].BoundingBox()

    # Две колонки строго на одном уровне вверху экрана
    col_ctrl, col_img = st.columns([1, 1.2])

    with col_ctrl:
        st.subheader("Управление шарнирами")
        h_options = [f"Шарнир №{i+1}" for i in range(len(st.session_state['hinge_list']))]
        selected = st.selectbox("Активный шарнир:", h_options, index=st.session_state['cur_h_idx'])
        h_idx = h_options.index(selected)
        st.session_state['cur_h_idx'] = h_idx

        cur_h = st.session_state['hinge_list'][h_idx]
        cur_h['type'] = st.selectbox("Тип шарнира:", ["normal", "ball"], index=0 if cur_h['type'] == 'normal' else 1)

        st.markdown(f"**X:** `{cur_h['x']:.1f} мм` | **Y:** `{cur_h['y']:.1f} мм` | **Угол:** `{cur_h['rot']:.0f}°`")

        # Кнопки перемещения
        st.write("Смещение:")
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            if st.button("⬅️ -5мм"):
                cur_h['x'] -= 5.0
                st.rerun()
        with p2:
            if st.button("➡️ +5мм"):
                cur_h['x'] += 5.0
                st.rerun()
        with p3:
            if st.button("⬇️ Вниз"):
                cur_h['y'] -= 5.0
                st.rerun()
        with p4:
            if st.button("⬆️ Вверх"):
                cur_h['y'] += 5.0
                st.rerun()

        # Поворот
        st.write("Поворот:")
        r1, r2 = st.columns(2)
        with r1:
            if st.button("🔄 -15°"):
                cur_h['rot'] -= 15.0
                st.rerun()
        with r2:
            if st.button("🔁 +15°"):
                cur_h['rot'] += 15.0
                st.rerun()

        st.write("---")
        add_c, rem_c = st.columns(2)
        with add_c:
            if st.button("➕ Добавить"):
                st.session_state['hinge_list'].append({'x': 0.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'})
                st.rerun()
        with rem_c:
            if st.button("🗑️ Удалить", disabled=(len(st.session_state['hinge_list']) <= 1)):
                st.session_state['hinge_list'].pop(h_idx)
                st.session_state['cur_h_idx'] = 0
                st.rerun()

        st.write("---")
        build_btn = st.button("🚀 Собрать модель (STL/STEP)", use_container_width=True)

    # Генерация предпросмотра
    scad_parts = []
    for i, h in enumerate(st.session_state['hinge_list']):
        is_active = (i == h_idx)
        bar_col = "red" if is_active else "navy"
        dot_col = "yellow" if is_active else "white"
        scad_parts.append(
            f'''
            translate([{h["x"]}, {h["y"]}, 0]) rotate([0, 0, {h["rot"]}]) {{
                color("{bar_col}") linear_extrude({st.session_state["height_val"] * 1.3}) square([3, {bbox.ylen * 1.5}], center=true);
                color("{dot_col}") translate([0, 0, {st.session_state["height_val"]}]) cylinder(d={st.session_state["height_val"] * 1.2}, h=2, center=true);
            }}
            '''
        )

    preview_code = f"""
    $fn=25;
    color("lightgreen") linear_extrude({st.session_state['height_val']}) import("file.dxf");
    {' '.join(scad_parts)}
    """
    with open("live_preview.scad", "w") as f:
        f.write(preview_code)

    subprocess.run(
        "xvfb-run -a openscad -o live_preview.png --autocenter --viewall --projection=ortho live_preview.scad",
        shell=True
    )

    with col_img:
        st.subheader("Предпросмотр")
        if os.path.exists("live_preview.png"):
            st.image("live_preview.png", caption="🟡 Желтый диск — активный шарнир | ⚪ Белый — остальные", use_container_width=True)

    if build_btn:
        with st.spinner("Генерация CAD-модели..."):
            current_height = st.session_state['height_val']
            res = cq.importers.importDXF("file.dxf").wires().toPending().extrude(current_height)

            for h in st.session_state['hinge_list']:
                h_dict = {
                    "type": h["type"],
                    "h_tran": [h["x"], h["y"]],
                    "h_rot": h["rot"],
                    "h_break": 3.0,
                    "h_break_len": bbox.ylen * 2.0,
                    "h_diam": current_height,
                    "h_thick": 5.0,
                    "h_expose": True
                }
                if h["type"] == "normal":
                    res = normal_hinge(h_dict, res, current_height)
                else:
                    res = ball_joint(h_dict, res, current_height)

            out_file = f"result.{out_format}"
            cq.exporters.export(res, out_file)
            st.success("Готово!")

            with open(out_file, "rb") as f:
                st.download_button(
                    label=f"💾 Скачать {out_format.upper()}",
                    data=f,
                    file_name=out_file,
                    mime=f"model/{out_format}",
                    use_container_width=True
                )
else:
    st.info("👈 Загрузите файл изображения в боковом меню слева, чтобы начать работу.")
