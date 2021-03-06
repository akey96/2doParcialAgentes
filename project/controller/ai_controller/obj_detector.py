import cv2
import numpy as np

UMBRAL = 60
COLORS = ['blue', 'green', 'red']
FIGURES = ['cube', 'tetrahedron', 'sphere']

def display_analysis(frame, contours, locations, color):
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.drawContours(frame, contours, -1, color, 2)
    locations = get_locations(contours)
    if locations.any():
         # actualizando de direccion
        for loc, c in zip(locations,contours):
            figure = find_figure(c)
            cx, cy = loc
            cv2.circle(frame,(cx, cy), 3, (0,255,255), -1)
            cv2.putText(frame,"(x: " + str(cx) + ", y: " + str(cy) + ")",(cx+10,cy+10), font, 0.5,(255,255,255),1)
            cv2.putText(frame, figure , (cx,cy-5),font,1,(0,255,0),1)

class Model_AI():
    def __init__(self):
        self.min_distance = UMBRAL
        self.color_detected = False
        self.current_direction = 0
        self.current_color = [0,0,255]
    
    def encode_color(self, color:str):
        encoded_color = (np.array(COLORS) == color).astype('int') * 255
        encoded_color = map(int, encoded_color)
        return list(encoded_color)
    
    def search_by_color(self, img, figure:str, color:str):
        self.current_color = self.encode_color(color)
        located = False
        mask = color_filter(img, self.current_color)
        contours = find_contours(mask)
        locations = get_locations(contours)
        center = np.int32(np.array(img.shape[:2]) // 2)
        display_analysis(img, contours, locations, self.current_color)
        if locations.any():
            located = True
            distances = np.linalg.norm(locations - np.array(list(reversed(center))), axis=1)
            min_index = np.argmin(distances)
            if distances.min() < UMBRAL:
                self.current_direction = int(self.min_distance > distances.min()) * self.current_direction
                self.min_distance = distances.min()
            else:
                vector = locations[min_index] - np.array(list(reversed(center)))
                vector = vector / (np.abs(vector).sum() * 0.5)
                vector = np.tanh(vector)
                self.current_direction = int(round(vector[0]))
        return located, self.current_direction

    def search_by_figure(self, img, figure:str, color):
        color = None
        figure = figure.lower()
        located = False
        if color is None and not self.color_detected:
            color, self.current_direction = detect_color(img)
            if color is not None:
                self.current_color = color
                self.color_detected = True
        elif not self.color_detected and color is not None:
            self.current_color = color
            self.color_detected = True

        if self.current_color is not None:
            mask = color_filter(img, self.current_color)
            contours = find_contours(mask)
            locations = get_locations(contours)
            new_location = locations.copy()
            for i in range(len(locations)):
                found_figure = find_figure(contours[i])
                if found_figure != figure:
                    new_location = new_location[new_location!=locations[i]]
                    if new_location.shape[0] >= 2:
                        new_location = new_location.reshape(-1,2)
                    else:
                        new_location = np.array([])
            locations = new_location
            center = np.int32(np.array(img.shape[:2]) // 2)
            display_analysis(img, contours, locations, self.current_color)
            if locations.any():
                located = True
                distances = np.linalg.norm(locations - np.array(list(reversed(center))), axis=1)
                min_index = np.argmin(distances)
                if distances.min() < UMBRAL:
                    self.current_direction = int(self.min_distance > distances.min()) * self.current_direction
                    self.min_distance = distances.min()
                    if self.current_direction == 0:
                        self.color_detected = False
                        self.current_color = None
                        self.min_distance = UMBRAL
                        self.current_direction = 0
                elif distances.min() >= UMBRAL:
                    vector = locations[min_index] - np.array(list(reversed(center)))
                    vector = vector / (np.abs(vector).sum() * 0.5)
                    vector = np.tanh(vector)
                    self.current_direction = int(round(vector[0]))

        return located, self.current_direction

    def serch_by_color_and_figure(self, img, figure:str, color:str):
        color = self.encode_color(color)
        return self.search_by_figure(img, figure, color)



def find_figure(c):
    figure = None
    area=cv2.contourArea(c)
    if (area > 3000):
        epsilon=0.009*cv2.arcLength(c,True)
        approx=cv2.approxPolyDP(c,epsilon,True)
        x,y,w,h = cv2.boundingRect(approx)
        if len(approx) < 6:
            figure = 'tetraedro'
        elif len(approx) > 10 and len(approx) < 20:
            figure = 'esfera'
        else:
            figure = 'cubo'
    return figure



def color_filter(img, color):
    """
    Metes una imagen y el color que quieres detectar [255,0,0]->Azul, [0,255,0]->Verde, [0,0,255] -> azul
    
    Return: una imagen con las mismas dimenciones a la original pero solo con siluetas blancas
    """
    c3, c2, c1 = max_color(color)
    mask = (img[:,:,c1] > img[:,:,c2]) * (img[:,:,c1] > img[:,:,c3])
    mask = mask * (img[:,:,c1] - img[:,:,c2]) > 25
    mask = mask * 255
    mask = np.uint8(mask)
    kernel = np.ones((5,5),np.uint8)
    mask = cv2.dilate(mask,kernel,iterations=3)
    mask = cv2.morphologyEx(mask,cv2.MORPH_OPEN,kernel, iterations = 4)
    mask = cv2.morphologyEx(mask,cv2.MORPH_CLOSE,kernel, iterations = 4)
    #mask = cv2.erode(mask,kernel,iterations=3)
    dist_transform = cv2.distanceTransform(mask,cv2.DIST_L2,5)
    _, mask = cv2.threshold(dist_transform,0.4*dist_transform.max(),255,0)
    mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    return mask

def find_contours(mask):
    mask = np.uint8(mask)
    mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    contours,_ = cv2.findContours(mask,1,2)
    return contours

def get_locations(contours):
    locations = []
    for i in contours:
        #Calcular el centro a partir de los momentos
        momentos = cv2.moments(i)
        if momentos['m00']:
            cx = int(momentos['m10']/momentos['m00'])
            cy = int(momentos['m01']/momentos['m00'])
        else:
            cx = int(momentos['m10'])
            cy = int(momentos['m01'])
        #Dibujar el centro
        locations.append([cx, cy])
    return np.int32(locations)

def detect_color(img):
    shape = img.shape[:2]
    left  = [[shape[0]//2-50, 20], [shape[0]//2+50, 60]]
    right = [[shape[0]//2-50, shape[1] - 60], [shape[0]//2+50, shape[1] - 20]]
    (ly1, lx1), (ly2, lx2) = left
    (ry1, rx1), (ry2, rx2) = right
    left_part    = img[ly1: ly2, lx1: lx2]
    right_part   = img[ry1: ry2, rx1: rx2]
    center_part  = img[shape[0]//2-50:shape[1]//2+20, shape[1]//2-50:shape[1]//2+20]
    left_color   = np.median(left_part, axis=(0,1))
    right_color  = np.median(right_part, axis=(0,1))
    center_color = np.median(center_part, axis=(0,1))
    #print(left_color, right_color,"   ", end="\r")
    color = None
    direction = 0
    if abs(center_color.max() - np.median(center_color)) > 40:
        color = center_color
    elif abs(left_color.max() - np.median(left_color)) > 40:
        direction = -1
        color = left_color
    elif abs(right_color.max() - np.median(right_color)) > 40:
        direction = 1
        color = right_color
    return color, direction

def max_color(color):
    color = color[:3]
    return np.argsort(color)

def figures(mask):
    slice1Copy = np.uint8(mask)
    slice = cv2.Canny(slice1Copy,1,100)
    canny=cv2.Canny(slice,10,150)
    canny=cv2.dilate(canny,None,iterations=1)
    canny=cv2.erode(canny,None,iterations=1)
    cnts,h = cv2.findContours(canny,cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        ret = ''
        area=cv2.contourArea(c)
        if (area > 3000):
            epsilon=0.009*cv2.arcLength(c,True)
            approx=cv2.approxPolyDP(c,epsilon,True)
            x,y,w,h = cv2.boundingRect(approx)

            if (len(approx) >= 6 and len(approx) <= 10) or (len(approx) == 4 and (w/h >= 0.95 or w/h <=1.05)):
                ret = 'Cubo'
            elif len(approx) == 4 or len(approx) == 3:
                ret = 'Tetraedro'
            elif len(approx) > 10:
                ret = 'Esfera'
    return ret

