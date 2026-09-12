"""
rapidresizer_core.py
----------------------
Reimplementación en Python de los 5 modos de
online.rapidresizer.com/photograph-to-pattern.php, extraída directamente
de su código fuente (effects.js + imgutil.js + photograph-to-pattern.js).

Los 5 modos (mismos nombres y orden que la web):
    Edges     -> mode "edges"
    Thin      -> mode "canny"
    Threshold -> mode "blobs"
    Adaptive  -> mode "adaptive"
    Color     -> mode "color-threshold"

Notas de fidelidad:
- Edges, Thin, Threshold y Adaptive son una réplica fiel de las fórmulas reales.
- Adaptive usa un promedio local por ventana; se aproxima con un box-filter
  (la web usa una imagen integral con recorte exacto en los bordes; aquí el
  resultado es prácticamente idéntico salvo un margen de pocos píxeles).
- Color (labThreshold) usa la fórmula de distancia de color real (deltaE CIE94)
  extraída del código, pero la web escala su umbral con una fórmula interna
  de un "web worker" que no vino incluido en el zip descargado. Aquí se expone
  ese umbral como "tolerancia" (0-100) para ajustarlo a ojo.
"""

import cv2
import numpy as np


# ---------------------------------------------------------------- utilidades ---

def to_luma(img_bgr: np.ndarray) -> np.ndarray:
    """Escala de grises con los mismos pesos que usa la web (Rec.709)."""
    b, g, r = cv2.split(img_bgr.astype(np.float64))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def gaussian_blur_gray(gray: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return gray
    return cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma, sigmaY=sigma)


def negate(img: np.ndarray) -> np.ndarray:
    return 255.0 - img


def edge_filter(img: np.ndarray, radius: int = 2) -> np.ndarray:
    """Kernel (2r+1)x(2r+1): todo -1 salvo el centro = tamaño-1."""
    size = 2 * radius + 1
    kernel = -np.ones((size, size), dtype=np.float64)
    kernel[radius, radius] = size * size - 1
    out = cv2.filter2D(img, ddepth=cv2.CV_64F, kernel=kernel, borderType=cv2.BORDER_REFLECT101)
    return np.clip(out, 0, 255)


def binary_threshold(img: np.ndarray, level: float) -> np.ndarray:
    return np.where(img >= level, 255, 0).astype(np.uint8)


def outline_canny(gray_u8: np.ndarray, low: float, high: float) -> np.ndarray:
    low = max(0.0, low)
    high = max(low + 1, high)
    return cv2.Canny(gray_u8, low, high)


# ------------------------------------------------------------------- modos ---

def mode_edges(img_bgr: np.ndarray, blur: float = 1.0, threshold: float = 128.0) -> np.ndarray:
    """'Edges': líneas negras sobre blanco, buena para line-art."""
    gray = to_luma(img_bgr)
    blurred = gaussian_blur_gray(gray, blur)
    inv = negate(blurred)
    edge = edge_filter(inv, radius=2)
    binary = binary_threshold(edge, threshold)
    return 255 - binary


def mode_thin(img_bgr: np.ndarray, blur: float = 1.0, threshold: float = 128.0) -> np.ndarray:
    """'Thin': bordes finos tipo Canny."""
    gray = to_luma(img_bgr)
    blurred = gaussian_blur_gray(gray, blur)
    gray_u8 = np.clip(blurred, 0, 255).astype(np.uint8)
    low = threshold / 3.0
    high = threshold
    edges = outline_canny(gray_u8, low, high)
    return 255 - edges


def mode_threshold(img_bgr: np.ndarray, blur: float = 1.0, threshold: float = 128.0,
                    outline: bool = False) -> np.ndarray:
    """'Threshold': áreas claras -> blanco, oscuras -> negro (con ecualización de histograma)."""
    gray = to_luma(img_bgr)
    blurred = gaussian_blur_gray(gray, blur)
    gray_u8 = np.clip(blurred, 0, 255).astype(np.uint8)
    equalized = cv2.equalizeHist(gray_u8)
    binary = binary_threshold(equalized.astype(np.float64), threshold)
    if outline:
        edges = outline_canny(binary, 50, 100)
        return 255 - edges
    return binary


def mode_adaptive(img_bgr: np.ndarray, blur: float = 1.0, threshold: float = 32.0,
                   outline: bool = False, blur_max: float = 4.0) -> np.ndarray:
    """'Adaptive': como Threshold pero compara contra el promedio local (mejor en sombras)."""
    gray = to_luma(img_bgr)
    gray_u8 = np.clip(gray, 0, 255).astype(np.uint8)
    h, w = gray_u8.shape
    radius = int(np.ceil(min(0.05 * min(w, h), 49) * blur / blur_max)) or 1
    win = 2 * radius + 1
    local_mean = cv2.boxFilter(gray_u8.astype(np.float64), ddepth=-1, ksize=(win, win),
                                borderType=cv2.BORDER_REPLICATE)
    frac = threshold / 255.0
    binary = np.where(gray_u8.astype(np.float64) > frac * local_mean, 255, 0).astype(np.uint8)
    if outline:
        edges = outline_canny(binary, 50, 100)
        return 255 - edges
    return binary


def mode_color(img_bgr: np.ndarray, target_rgb, blur: float = 1.0, tolerance: float = 25.0,
               outline: bool = False) -> np.ndarray:
    """'Color': áreas parecidas al color elegido -> negro, el resto -> blanco.

    tolerance (0-100 aprox.): distancia de color (deltaE) máxima para considerarse
    "parecido". Sube el valor para capturar más tonos alrededor del color elegido.
    """
    img = img_bgr.astype(np.float64)
    if blur > 0:
        k = 7  # 2*3+1, kernelSize=3 fijo como en la web
        img = cv2.GaussianBlur(img, (k, k), sigmaX=blur, sigmaY=blur)

    img_lab = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float64)
    # OpenCV Lab: L en 0-255 (no 0-100), a/b desplazados +128. Reescalamos a la
    # convención estándar (L 0-100, a/b con signo) para que 'tolerance' sea comparable.
    L = img_lab[..., 0] * (100.0 / 255.0)
    A = img_lab[..., 1] - 128.0
    B = img_lab[..., 2] - 128.0

    target_bgr = np.uint8([[[target_rgb[2], target_rgb[1], target_rgb[0]]]])
    target_lab = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2LAB).astype(np.float64)[0, 0]
    tL = target_lab[0] * (100.0 / 255.0)
    tA = target_lab[1] - 128.0
    tB = target_lab[2] - 128.0

    dL = L - tL
    C1 = np.sqrt(A ** 2 + B ** 2)
    C2 = np.sqrt(tA ** 2 + tB ** 2)
    dC = C1 - C2
    dH_sq = (A - tA) ** 2 + (B - tB) ** 2 - dC ** 2
    dH = np.sqrt(np.clip(dH_sq, 0, None))
    deltaE = np.sqrt(dL ** 2 + (dC / (1 + 0.045 * C1)) ** 2 + (dH / (1 + 0.015 * C1)) ** 2)

    binary = np.where(deltaE <= tolerance, 0, 255).astype(np.uint8)
    if outline:
        edges = outline_canny(binary, 50, 100)
        return 255 - edges
    return binary
