# USAGE
# python extract_embeddings.py --dataset dataset --embeddings output/embeddings.pickle --detector face_detection_model --embedding-model openface_nn4.small2.v1.t7
# celeba dataset python extract_by_PCA.py --dataset C:/Users/sorjt/Desktop/drive-download-20210429T145212Z-001/archive/img_align_celeba/img_align_celeba  --embeddings output/embeddings.pickle --detector face_detection_model --embedding-model openface_nn4.small2.v1.t7
# import the necessary packages
from imutils import paths
import numpy as np
import argparse
import imutils
import pickle
import cv2
import openface
import os
import dlib
from sklearn.decomposition import PCA
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--dataset", required=True,
	help="path to input directory of faces + images")
ap.add_argument("-e", "--embeddings", required=True,
	help="path to output serialized db of facial embeddings")
ap.add_argument("-d", "--detector", required=True,
	help="path to OpenCV's deep learning face detector")
ap.add_argument("-m", "--embedding-model", required=True,
	help="path to OpenCV's deep learning face embedding model")
ap.add_argument("-c", "--confidence", type=float, default=0.5,
	help="minimum probability to filter weak detections")
args = vars(ap.parse_args())

# load our serialized face detector from disk
print("[INFO] loading face detector...")
protoPath = os.path.sep.join([args["detector"], "deploy.prototxt"])
modelPath = os.path.sep.join([args["detector"],
	"res10_300x300_ssd_iter_140000.caffemodel"])
detector = cv2.dnn.readNetFromCaffe(protoPath, modelPath)
predictor_model="../landmark/shape_predictor_68_face_landmarks.dat"
# load our serialized face embedding model from disk
print("[INFO] loading face recognizer...")
embedder = cv2.dnn.readNetFromTorch(args["embedding_model"])

# grab the paths to the input images in our dataset
print("[INFO] quantifying faces...")
imagePaths = list(paths.list_images(args["dataset"]))
pca=PCA(n_components=128)
# initialize our lists of extracted facial embeddings and
# corresponding people names
knownEmbeddings = []
knownNames = []
face_aligner=openface.AlignDlib(predictor_model)
# initialize the total number of faces processed
total = 0

# loop over the image paths
for (i, imagePath) in enumerate(imagePaths):
	# extract the person name from the image path
    print("[INFO] processing image {}/{}".format(i + 1,len(imagePaths)))
    name = imagePath.split(os.path.sep)[-2]

	# load the image, resize it to have a width of 600 pixels (while
	# maintaining the aspect ratio), and then grab the image
	# dimensions
    image = cv2.imread(imagePath)
    image = imutils.resize(image, width=600)
    (h, w) = image.shape[:2]

	# construct a blob from the image
    imageBlob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0, (300, 300),(104.0, 177.0, 123.0), swapRB=False, crop=False)

	# apply OpenCV's deep learning-based face detector to localize
	# faces in the input image
    detector.setInput(imageBlob)
    detections = detector.forward()

	# ensure at least one face was found
    if len(detections) > 0:
		# we're making the assumption that each image has only ONE
		# face, so find the bounding box with the largest probability
        i = np.argmax(detections[0, 0, :, 2])
        confidence = detections[0, 0, i, 2]

		# ensure that the detection with the largest probability also
		# means our minimum probability test (thus helping filter out
		# weak detections)
        if confidence > args["confidence"]:
			# compute the (x, y)-coordinates of the bounding box for
			# the face
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

			# extract the face ROI and grab the ROI dimensions
            #face = image[startY:endY, startX:endX]

            left=startX
            right=endX
            top=startY
            bottom=endY
            rect=dlib.rectangle(left,top,right,bottom)
            size=max([endX-startX,endY-startY])
            face=face_aligner.align(size,image,rect,landmarkIndices=openface.AlignDlib.OUTER_EYES_AND_NOSE)
            (fH, fW) = face.shape[:2]

			# ensure the face width and height are sufficiently large
            if fW < 20 or fH < 20:
                continue

			# construct a blob for the face ROI, then pass the blob
			# through our face embedding model to obtain the 128-d
			# quantification of the face

			# faceBlob = cv2.dnn.blobFromImage(face, 1.0 / 255,(96, 96), (0, 0, 0), swapRB=True, crop=False)
			# embedder.setInput(faceBlob)
			# vec = embedder.forward()

			# add the name of the person + corresponding face
			# embedding to their respective lists
            face=cv2.cvtColor(face,cv2.COLOR_BGR2GRAY)
            face=cv2.resize(face,dsize=(47,62),interpolation=cv2.INTER_AREA)
            knownNames.append(name)
            knownEmbeddings.append(face.flatten())
            total += 1

# dump the facial embeddings + names to disk
print("[INFO] serializing {} encodings...".format(total))
knownEmbeddings=pca.fit_transform(knownEmbeddings)
data = {"embeddings": knownEmbeddings, "names": knownNames}
f = open(args["embeddings"], "wb")
f.write(pickle.dumps(data))
f.close()