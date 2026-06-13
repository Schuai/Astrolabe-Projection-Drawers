from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import cv2
import numpy as np


WINDOW_NAME = "Perspective Corrector"
POINT_RADIUS = 6
LINE_THICKNESS = 2
TEXT_COLOR = (245, 245, 245)
POINT_COLOR = (0, 215, 255)
EDGE_COLOR = (80, 220, 80)
PANEL_COLOR = (24, 24, 24)
PANEL_ALPHA = 0.75
MODE_B: Literal["b"] = "b"
MODE_C: Literal["c"] = "c"


@dataclass
class AppState:
    original_image: np.ndarray
    current_image: np.ndarray
    output_path: Path
    mode: Literal["b", "c"] | None = None
    points: list[tuple[float, float]] = field(default_factory=list)
    corrected_image: np.ndarray | None = None
    awaiting_click: bool = False
    showing_corrected: bool = False
    mode_message: str | None = None

    def reset_to_original(self) -> None:
        self.current_image = self.original_image.copy()
        self.mode = None
        self.points.clear()
        self.corrected_image = None
        self.awaiting_click = False
        self.showing_corrected = False
        self.mode_message = None

    def restart_from_corrected(self) -> None:
        if self.corrected_image is None:
            return
        self.current_image = self.corrected_image.copy()
        self.mode = None
        self.points.clear()
        self.corrected_image = None
        self.awaiting_click = False
        self.showing_corrected = False
        self.mode_message = None

    @property
    def required_points(self) -> int:
        if self.mode == MODE_B:
            return 4
        if self.mode == MODE_C:
            return 3
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactively rectify a quadrilateral region into a square."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        required=True,
        help="Input image path.",
    )
    parser.add_argument(
        "--save-path",
        type=Path,
        required=True,
        help="Output image path.",
    )
    return parser.parse_args()


def distance(point_a: np.ndarray, point_b: np.ndarray) -> float:
    return float(np.linalg.norm(point_a - point_b))


def quadrilateral_area(points: np.ndarray) -> float:
    x_values = points[:, 0]
    y_values = points[:, 1]
    return 0.5 * abs(
        np.dot(x_values, np.roll(y_values, -1)) - np.dot(y_values, np.roll(x_values, -1))
    )


def validate_mode_b_points(point_array: np.ndarray) -> None:
    for index in range(4):
        segment_length = distance(point_array[index], point_array[(index + 1) % 4])
        if segment_length <= 1e-6:
            raise ValueError("Adjacent selected points are too close together.")
    if quadrilateral_area(point_array) <= 1.0:
        raise ValueError("Selected quadrilateral is too small or degenerate.")


def square_target_size(point_array: np.ndarray) -> int:
    edge_lengths = [
        distance(point_array[index], point_array[(index + 1) % 4]) for index in range(4)
    ]
    side_length = int(round(sum(edge_lengths) / len(edge_lengths)))
    return max(side_length, 2)


def rectify_mode_b(image: np.ndarray, points: list[tuple[float, float]]) -> np.ndarray:
    point_array = np.asarray(points, dtype=np.float32)
    validate_mode_b_points(point_array)

    side_length = square_target_size(point_array)
    destination = np.asarray(
        [
            [0.0, 0.0],
            [side_length - 1.0, 0.0],
            [side_length - 1.0, side_length - 1.0],
            [0.0, side_length - 1.0],
        ],
        dtype=np.float32,
    )

    homography = cv2.getPerspectiveTransform(point_array, destination)
    return cv2.warpPerspective(
        image,
        homography,
        (side_length, side_length),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )


def rectify_image(
    image: np.ndarray, mode: Literal["b", "c"], points: list[tuple[float, float]]
) -> np.ndarray:
    if mode == MODE_B:
        return rectify_mode_b(image, points)
    raise NotImplementedError(
        "Mode c is not implemented because three points on a circle are not enough for a reliable perspective rectification."
    )


def draw_mode_selection(display: np.ndarray) -> None:
    lines = [
        "Choose mode first",
        "b Quadrilateral to square",
        "c Circle mode (not implemented)",
    ]
    for index, text in enumerate(lines):
        cv2.putText(
            display,
            text,
            (16, 30 + index * 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            TEXT_COLOR,
            2,
            cv2.LINE_AA,
        )


def draw_point_edges(display: np.ndarray, points: list[tuple[float, float]], close_shape: bool) -> None:
    for index, point in enumerate(points):
        point_xy = (int(round(point[0])), int(round(point[1])))
        cv2.circle(display, point_xy, POINT_RADIUS, POINT_COLOR, -1)
        cv2.circle(display, point_xy, POINT_RADIUS + 2, EDGE_COLOR, 2)
        cv2.putText(
            display,
            str(index + 1),
            (point_xy[0] + 10, point_xy[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            EDGE_COLOR,
            2,
            cv2.LINE_AA,
        )

    for index in range(1, len(points)):
        start = tuple(int(round(value)) for value in points[index - 1])
        end = tuple(int(round(value)) for value in points[index])
        cv2.line(display, start, end, EDGE_COLOR, LINE_THICKNESS, cv2.LINE_AA)

    if close_shape and len(points) >= 4:
        start = tuple(int(round(value)) for value in points[-1])
        end = tuple(int(round(value)) for value in points[0])
        cv2.line(display, start, end, EDGE_COLOR, LINE_THICKNESS, cv2.LINE_AA)


def draw_overlay(state: AppState) -> np.ndarray:
    canvas = state.current_image.copy() if not state.showing_corrected else state.corrected_image.copy()
    if canvas is None:
        raise RuntimeError("No image available for display.")

    display = canvas.copy()
    panel_height = 140
    overlay = display.copy()
    cv2.rectangle(overlay, (0, 0), (display.shape[1], panel_height), PANEL_COLOR, -1)
    cv2.addWeighted(overlay, PANEL_ALPHA, display, 1.0 - PANEL_ALPHA, 0.0, display)

    if state.mode is None:
        draw_mode_selection(display)
        if state.mode_message is not None:
            cv2.putText(
                display,
                state.mode_message,
                (16, 120),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.62,
                TEXT_COLOR,
                2,
                cv2.LINE_AA,
            )
        return display

    draw_point_edges(display, state.points, close_shape=state.mode == MODE_B)

    if state.showing_corrected:
        lines = [
            f"Mode: {state.mode} corrected preview",
            "s Save and exit    q Exit without saving",
            "r Restart from original    a Continue from corrected image",
        ]
    else:
        waiting_suffix = "    Click once to add the next point" if state.awaiting_click else ""
        lines = [
            f"Mode: {state.mode}    Points: {len(state.points)}/{state.required_points}{waiting_suffix}",
            "a Arm one point add    d Delete the latest point",
            "Press Enter after all points to rectify",
        ]

    for index, text in enumerate(lines):
        cv2.putText(
            display,
            text,
            (16, 30 + index * 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            TEXT_COLOR,
            2,
            cv2.LINE_AA,
        )

    return display


def on_mouse(event: int, x: int, y: int, _flags: int, userdata: AppState) -> None:
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    if userdata.mode is None or userdata.showing_corrected:
        return
    if not userdata.awaiting_click or len(userdata.points) >= userdata.required_points:
        return

    userdata.points.append((float(x), float(y)))
    userdata.awaiting_click = False


def main() -> None:
    args = parse_args()
    image_path = args.input_path
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Failed to read image: {image_path}")

    output_path = args.save_path
    state = AppState(
        original_image=image.copy(),
        current_image=image.copy(),
        output_path=output_path,
    )

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse, state)

    while True:
        cv2.imshow(WINDOW_NAME, draw_overlay(state))
        key = cv2.waitKey(20) & 0xFF

        if key == 255:
            continue
        if key == ord("q"):
            break

        if state.mode is None:
            if key == ord("b"):
                state.mode = MODE_B
                state.mode_message = None
            elif key == ord("c"):
                state.mode = MODE_C
                state.mode_message = "Mode c selected, but it is not implemented."
            continue

        if key == ord("d") and not state.showing_corrected and state.points:
            state.points.pop()
            state.awaiting_click = False
            continue

        if key == ord("a"):
            if state.showing_corrected:
                state.restart_from_corrected()
            elif len(state.points) < state.required_points:
                state.awaiting_click = True
            continue

        if key == ord("r") and state.showing_corrected:
            state.reset_to_original()
            continue

        if key == ord("s") and state.showing_corrected and state.corrected_image is not None:
            state.output_path.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(state.output_path), state.corrected_image):
                raise IOError(f"Failed to save image: {state.output_path}")
            break

        if key in (13, 10) and not state.showing_corrected:
            if state.mode == MODE_C:
                raise NotImplementedError(
                    "Mode c is not implemented because three points on a circle are not enough for a reliable perspective rectification."
                )
            if len(state.points) == state.required_points:
                state.corrected_image = rectify_image(state.current_image, state.mode, state.points)
                state.showing_corrected = True
                state.awaiting_click = False

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
