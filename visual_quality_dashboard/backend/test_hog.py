from skimage.feature import hog
import numpy as np

arr = np.zeros((128, 128), dtype=np.uint8)
f = hog(arr, orientations=9, pixels_per_cell=(16, 16), cells_per_block=(2, 2), block_norm='L2-Hys')
print('HOG OK, feature vector length:', f.shape)
