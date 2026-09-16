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
        .box(h['h_break'], h['h_break_len'], height, centered=(True, True, False))
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    chamfer_top = (
        cq.Workplane('XY')
        .box(chamfer, h['h_break_len'], chamfer, centered=(True, True, True))
        .rotate([0, 0, 0], [0, 1, 0], 45)
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    chamfer_bot = (
        cq.Workplane('XY')
        .box(chamfer, h['h_break_len'], chamfer, centered=(True, True, True))
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
        .box(hole_h_im_x, h['h_thick'] + hor_tolerance * 2, height, centered=(True, True, False))
        .translate([-hole_h_im_x / 2 - h['h_break'] / 2, 0, 0])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    res -= hole_im

    hole_diam = pin_diam + vert_tolerance
    hinge_corn = (
        cq.Workplane('XZ')
        .box(hole_h_im_x / 2 + chamfer * math.sqrt(2), h['h_diam'], h['h_thick'], centered=(False, False, True))
        .translate([-h['h_break'] / 2 - pin_diam / 2, 0, height / 2 - h['h_diam'] / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hinge_ext = (
        cq.Workplane('XZ')
        .cylinder(h['h_thick'], h['h_diam'] / 2, centered=(True, False, True))
        .translate([x_hinge, 0, height / 2 - h['h_diam'] / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hinge_hole = (
        cq.Workplane('XZ')
        .cylinder(h['h_thick'], hole_diam / 2, centered=(True, False, True))
        .translate([x_hinge, 0, height / 2 - hole_diam / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hinge_pin = (
        cq.Workplane('XZ')
        .cylinder(h['h_thick'] + hor_tolerance * 2, pin_diam / 2, centered=(True, False, True))
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
    hole_join = (
        cq.Workplane('XY')
        .box(h['h_break'] + (h['h_diam'] / 2 + hor_tolerance) * 2, h['h_diam'] / 2 + hor_tolerance, height, centered=(True, True, False))
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
st.title("Flexifier: Интерактивный редактор")

# Инициализация параметров
if 'height_val' not in st.session_state:
    st.session_state['height_val'] = 8.0
if 'hinge_list' not in st.session_state:
    # По умолчанию создаем 3 шарнира поперек тела
    st.session_state['hinge_list'] = [
        {'x': -30.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'},
        {'x': 0.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'},
        {'x': 30.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'}
    ]
if 'cur_h_idx' not in st.session_state:
    st.session_state['cur_h_idx'] = 0

col_settings, col_view = st.columns([1, 2])

with col_settings:
    filetype = st.selectbox("Формат файла", ["jpg", "png", "jpeg", "svg"])
    out_format = st.selectbox("Формат сохранения", ["stl", "step"])

    st.write(f"**Толщина детали (Z):** {st.session_state['height_val']:.1f} мм")
    hb1, hb2 = st.columns(2)
    with hb1:
        if st.button("➖ Тоньше"):
            st.session_state['height_val'] = max(2.0, st.session_state['height_val'] - 1.0)
            st.rerun()
    with hb2:
        if st.button("➕ Толще"):
            st.session_state['height_val'] = min(50.0, st.session_state['height_val'] + 1.0)
            st.rerun()

    uploaded_file = st.file_uploader("Загрузите файл", type=[filetype])

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

    # Чистим старый DXF перед сборкой
    if os.path.exists("file.dxf"):
        os.remove("file.dxf")

    with open("svg_to_dxf.scad", "w") as f:
        f.write('scale([0.4, 0.4, 1]) import(file = "file.svg", center = true);')
    subprocess.run("openscad svg_to_dxf.scad -o file.dxf", shell=True)

    base_model = cq.importers.importDXF("file.dxf").wires().toPending().extrude(st.session_state['height_val'])
    bbox = base_model.combine().objects[0].BoundingBox()

    with col_settings:
        st.write("---")
        st.write("### Управление шарнирами:")
        h_options = [f"Шарнир №{i+1}" for i in range(len(st.session_state['hinge_list']))]
        selected = st.selectbox("Выберите активный шарнир:", h_options, index=st.session_state['cur_h_idx'])
        h_idx = h_options.index(selected)
        st.session_state['cur_h_idx'] = h_idx

        cur_h = st.session_state['hinge_list'][h_idx]

        cur_h['type'] = st.selectbox("Тип соединения:", ["normal", "ball"], index=0 if cur_h['type'] == 'normal' else 1)

        st.write(f"Позиция X: **{cur_h['x']:.1f} мм** | Y: **{cur_h['y']:.1f} мм**")
        
        # Кнопки перемещения выбранного шарнира
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

        r1, r2 = st.columns(2)
        with r1:
            if st.button("🔄 Повернуть (-15°)"):
                cur_h['rot'] -= 15.0
                st.rerun()
        with r2:
            if st.button("🔁 Повернуть (+15°)"):
                cur_h['rot'] += 15.0
                st.rerun()

        st.write("---")
        add_col, rem_col = st.columns(2)
        with add_col:
            if st.button("➕ Добавить шарнир"):
                st.session_state['hinge_list'].append({'x': 0.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'})
                st.rerun()
        with rem_col:
            if st.button("🗑️ Удалить шарнир", disabled=(len(st.session_state['hinge_list']) <= 1)):
                st.session_state['hinge_list'].pop(h_idx)
                st.session_state['cur_h_idx'] = 0
                st.rerun()

    # Генерация OpenSCAD предпросмотра
    scad_preview_parts = []
    for i, h in enumerate(st.session_state['hinge_list']):
        col = "red" if i == h_idx else "blue"
        scad_preview_parts.append(
            f'translate([{h["x"]}, {h["y"]}, 0]) rotate([0, 0, {h["rot"]}]) '
            f'color("{col}") linear_extrude({st.session_state["height_val"] * 1.2}) square([3, {bbox.ylen * 1.5}], center=true);'
        )

    preview_scad_code = f"""
    $fn=15;
    color("lightgreen") linear_extrude({st.session_state['height_val']}) import("file.dxf");
    {' '.join(scad_preview_parts)}
    """
    with open("live_preview.scad", "w") as f:
        f.write(preview_scad_code)

    subprocess.run("xvfb-run -a openscad -o live_preview.png --autocenter --viewall live_preview.scad", shell=True)

    with col_view:
        if os.path.exists("live_preview.png"):
            st.image("live_preview.png", caption="🟢 Тело рыбы | 🔴 Активный разрез | 🔵 Остальные разрезы", use_container_width=True)

        if st.button("🚀 Собрать финальную модель (STL/STEP)", use_container_width=True):
            with st.spinner("Генерация CAD-геометрии..."):
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
                st.success("Модель успешно сгенерирована!")

                with open(out_file, "rb") as f:
                    st.download_button(
                        label=f"💾 Скачать результат ({out_format.upper()})",
                        data=f,
                        file_name=out_file,
                        mime=f"model/{out_format}",
                        use_container_width=True
                    )
