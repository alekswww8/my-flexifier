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
st.title("Flexifier: Интерактивный редактор без слайдеров")

if 'height_val' not in st.session_state:
    st.session_state['height_val'] = 8.0

col_settings, col_canvas = st.columns([1, 2])

with col_settings:
    filetype = st.selectbox("Формат файла", ["png", "jpg", "jpeg", "svg"])
    out_format = st.selectbox("Формат сохранения", ["stl", "step"])
    tool_mode = st.radio("Действие мыши на поле:", ["Масштабирование (рамка)", "Рисование шарниров (линии)"])
    hinge_type = st.selectbox("Тип шарнира", ["normal", "ball"])

    st.write(f"**Толщина детали (Z):** {st.session_state['height_val']:.1f} мм")
    h_b1, h_b2 = st.columns(2)
    with h_b1:
        if st.button("➖ Уменьшить толщину"):
            st.session_state['height_val'] = max(2.0, st.session_state['height_val'] - 1.0)
            st.rerun()
    with h_b2:
        if st.button("➕ Увеличить толщину"):
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

    c_width, c_height = 650, 450
    bg_img = Image.open(raw_path if filetype != "svg" else "file.pnm").convert("RGBA")

    # Исходная рамка масштабирования
    init_drawing = {
        "version": "4.4.0",
        "objects": [{
            "type": "rect",
            "left": 100,
            "top": 50,
            "width": 300,
            "height": 300,
            "fill": "rgba(0, 150, 255, 0.15)",
            "stroke": "#0066FF",
            "strokeWidth": 2
        }]
    }

    with col_canvas:
        if tool_mode == "Масштабирование (рамка)":
            st.info("👆 **Тяните за углы синей рамки мышью**, чтобы уменьшить или увеличить модель.")
            canvas_result = st_canvas(
                fill_color="rgba(0, 150, 255, 0.15)",
                stroke_width=2,
                stroke_color="#0066FF",
                background_image=bg_img,
                update_streamlit=True,
                height=c_height,
                width=c_width,
                drawing_mode="rect",
                initial_drawing=init_drawing,
                key="canvas_rect"
            )
        else:
            st.info("✏️ **Проведите линии разрезов мышкой** в местах, где должны гнуться шарниры.")
            canvas_result = st_canvas(
                stroke_width=3,
                stroke_color="#FF0000",
                background_image=bg_img,
                update_streamlit=True,
                height=c_height,
                width=c_width,
                drawing_mode="line",
                key="canvas_lines"
            )

    # Получение масштаба из рамки
    scale_factor_x = 1.0
    scale_factor_y = 1.0
    if canvas_result.json_data is not None:
        for obj in canvas_result.json_data.get("objects", []):
            if obj.get("type") == "rect":
                w = obj.get("width", 300) * obj.get("scaleX", 1.0)
                h = obj.get("height", 300) * obj.get("scaleY", 1.0)
                scale_factor_x = w / 300.0
                scale_factor_y = h / 300.0

    # Сбор линий шарниров
    hinges = []
    if canvas_result.json_data is not None:
        for obj in canvas_result.json_data.get("objects", []):
            if obj.get("type") == "line":
                x1, y1 = obj["left"], obj["top"]
                x2, y2 = x1 + obj["width"], y1 + obj["height"]
                cx = (x1 + x2) / 2.0 - (c_width / 2.0)
                cy = -((y1 + y2) / 2.0 - (c_height / 2.0))
                dx = x2 - x1
                dy = -(y2 - y1)
                length = math.sqrt(dx**2 + dy**2)
                angle = math.degrees(math.atan2(dy, dx))

                hinges.append({
                    "type": hinge_type,
                    "h_tran": [cx * 0.4, cy * 0.4],
                    "h_rot": angle,
                    "h_break": 3.0,
                    "h_break_len": max(length * 0.4, 25.0),
                    "h_diam": st.session_state['height_val'],
                    "h_thick": 5.0,
                    "h_expose": True
                })

    with col_settings:
        st.write(f"Масштаб по ширине (X): **{int(scale_factor_x * 100)}%**")
        st.write(f"Масштаб по длине (Y): **{int(scale_factor_y * 100)}%**")
        st.write(f"Шарниров нарисовано: **{len(hinges)}**")

        if st.button("🚀 Собрать модель"):
            with st.spinner("Экструзия и расчет геометрии..."):
                current_height = st.session_state['height_val']
                scad_code = f'scale([{0.4 * scale_factor_x}, {0.4 * scale_factor_y}, 1]) import("file.svg", center=true);'
                subprocess.run(f'openscad -e \'{scad_code}\' -o file.dxf', shell=True)

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
