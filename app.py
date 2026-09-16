import base64
import math
import os
import subprocess
import time
import cadquery as cq
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

hor_tolerance = 0.8
vert_tolerance = 0.8
chamfer_multi = 1


def cut_image(h, res, height):
    chamfer = h['h_break'] * chamfer_multi
    cut_im = (
        cq.Workplane('XY')
        .box(h['h_break'], h['h_break_len'], height * 1.5, centered=(True, True, True))
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], height / 2])
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
        .box(hole_h_im_x, h['h_thick'] + hor_tolerance * 2, height * 1.2, centered=(True, True, True))
        .translate([-hole_h_im_x / 2 - h['h_break'] / 2, 0, height / 2])
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
    if h.get('h_expose', True):
        hole_join = (
            cq.Workplane('XY')
            .box(h['h_break'] + (h['h_diam'] / 2 + hor_tolerance) * 2, h['h_diam'] / 2 + hor_tolerance, height, centered=(True, True, False))
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
st.title("Flexifier: Интерактивный редактор")

if 'height_val' not in st.session_state:
    st.session_state['height_val'] = 8.0
if 'scale_val' not in st.session_state:
    st.session_state['scale_val'] = 100

col_settings, col_canvas = st.columns([1, 2])

with col_settings:
    filetype = st.selectbox("Формат файла", ["jpg", "png", "jpeg", "svg"])
    out_format = st.selectbox("Формат сохранения", ["stl", "step"])
    hinge_type = st.selectbox("Тип шарнира", ["normal", "ball"])

    st.write(f"**Размер картинки:** {st.session_state['scale_val']}%")
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("🔍 Больше (+20%)"):
            st.session_state['scale_val'] = min(400, st.session_state['scale_val'] + 20)
            st.rerun()
    with sc2:
        if st.button("🔎 Меньше (-20%)"):
            st.session_state['scale_val'] = max(20, st.session_state['scale_val'] - 20)
            st.rerun()

    st.write(f"**Толщина детали (Z):** {st.session_state['height_val']:.1f} мм")
    hb1, hb2 = st.columns(2)
    with hb1:
        if st.button("➖ Тоньше (-1 мм)"):
            st.session_state['height_val'] = max(2.0, st.session_state['height_val'] - 1.0)
            st.rerun()
    with hb2:
        if st.button("➕ Толще (+1 мм)"):
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

    cur_scale = st.session_state['scale_val'] / 100.0
    scale_val = 0.4 * cur_scale
    with open("svg_to_dxf.scad", "w") as f:
        f.write(f'scale([{scale_val}, {scale_val}, 1]) import(file = "file.svg", center = true);')
    subprocess.run("openscad svg_to_dxf.scad -o file.dxf", shell=True)

    base_model = cq.importers.importDXF("file.dxf").wires().toPending().extrude(st.session_state['height_val'])
    bbox = base_model.combine().objects[0].BoundingBox()

    raw_img = Image.open(raw_path if filetype != "svg" else "file.pnm").convert("RGBA")
    base_w = 600
    base_h = int(raw_img.height * (base_w / raw_img.width))
    c_width = int(base_w * cur_scale)
    c_height = int(base_h * cur_scale)
    bg_img = raw_img.resize((c_width, c_height))

    with col_canvas:
        st.info("✏️ **Проведите линии мышкой** поперёк детали в местах шарниров:")
        canvas_result = st_canvas(
            stroke_width=4,
            stroke_color="#FF0000",
            background_image=bg_img,
            update_streamlit=True,
            height=c_height,
            width=c_width,
            drawing_mode="line",
            key="fixed_canvas"
        )

    hinges = []
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data.get("objects", [])
        for obj in objects:
            x1 = obj.get("x1", obj.get("left", 0))
            y1 = obj.get("y1", obj.get("top", 0))
            x2 = obj.get("x2", x1 + obj.get("width", 0))
            y2 = obj.get("y2", y1 + obj.get("height", 0))

            # Перевод координат от центра изображения к CAD-центру детали
            norm_x = (x1 + x2) / 2.0 / c_width - 0.5
            norm_y = (y1 + y2) / 2.0 / c_height - 0.5

            cq_x = norm_x * bbox.xlen + (bbox.xmin + bbox.xmax) / 2.0
            cq_y = -norm_y * bbox.ylen + (bbox.ymin + bbox.ymax) / 2.0

            dx = (x2 - x1) * (bbox.xlen / c_width)
            dy = -(y2 - y1) * (bbox.ylen / c_height)
            line_len = math.sqrt(dx**2 + dy**2)
            angle = math.degrees(math.atan2(dy, dx)) - 90.0

            hinges.append({
                "type": hinge_type,
                "h_tran": [cq_x, cq_y],
                "h_rot": angle,
                "h_break": 3.0,
                "h_break_len": max(line_len * 1.6, bbox.ylen * 1.5),
                "h_diam": st.session_state['height_val'],
                "h_thick": max(st.session_state['height_val'] * 0.5, 4.0),
                "h_expose": True
            })

    with col_settings:
        st.write(f"Шарниров нарисовано: **{len(hinges)}**")

        if st.button("🚀 Собрать модель"):
            if len(hinges) == 0:
                st.warning("Нарисуйте хотя бы одну линию на изображении!")
            else:
                with st.spinner("Вырезание шарниров..."):
                    current_height = st.session_state['height_val']
                    res = cq.importers.importDXF("file.dxf").wires().toPending().extrude(current_height)

                    for h in hinges:
                        if h["type"] == "normal":
                            res = normal_hinge(h, res, current_height)
                        else:
                            res = ball_joint(h, res, current_height)

                    out_file = f"result.{out_format}"
                    cq.exporters.export(res, out_file)
                    st.success("Готово!")

                    with open(out_file, "rb") as f:
                        st.download_button(
                            label=f"Скачать результат ({out_format.upper()})",
                            data=f,
                            file_name=out_file,
                            mime=f"model/{out_format}"
                        )
