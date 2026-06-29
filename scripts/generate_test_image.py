#!/usr/bin/env python3
"""Generate a test image of a book for API testing."""
import cv2
import numpy as np

img = np.ones((480, 640, 3), dtype=np.uint8) * 200
cv2.rectangle(img, (100, 60), (400, 350), (40, 60, 160), -1)
cv2.putText(img, "BOOK", (180, 220),
            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
cv2.imwrite("scripts/test_book.png", img)
print("Created scripts/test_book.png")
