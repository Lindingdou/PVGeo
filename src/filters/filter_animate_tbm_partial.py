Name = 'AnimatePartialTBM'
Label = 'Animate Partial Tunnel Boring Machine'
FilterCategory = 'CSM GP Filters'
Help = 'This filter analyzes a vtkTable containing position information about a Tunnel Boring Machine (TBM). This Filter iterates over each row of the table as a timestep and uses the XYZ coordinates of a single parts of the TBM to generate a tube that represents taht part of the TBM. To create a directional vector for the length of the cylider that represents the TBM component, this filter searches for the next different point and gets a unit vector bewtween the two. Then two points are constructed in the positive and negative directions of that vector for the ends of the cylinder.'
NumberOfInputs = 1
InputDataType = 'vtkTable'
OutputDataType = 'vtkPolyData'
# Have two array selection drop downs for the two arrays to correlate
NumberOfInputArrayChoices = 3
ExtraXml = '''\
    <DoubleVectorProperty
      name="TimestepValues"
      repeatable="1"
      information_only="1">
      <TimeStepsInformationHelper/>
          <Documentation>
          Available timestep values.
          </Documentation>
    </DoubleVectorProperty>
'''

InputArrayLabels = ['Easting', 'Northing', 'Elevation']

Properties = dict(
    Diameter=17.45,
    Length=1.66,
    dt=1.0
)

PropertiesHelp = dict(
)


def RequestData():
    import numpy as np
    from vtk.numpy_interface import dataset_adapter as dsa
    import PVGPpy.helpers as inputhelp
    from PVGPpy.filt import pointsToTube
    # Get input/output of Proxy
    pdi = self.GetInput()
    pdo = self.GetOutput()
    # Grab input arrays to process from drop down menus
    #- Grab all fields for input arrays:
    fields = []
    for i in range(3):
        fields.append(inputhelp.getSelectedArrayField(self, i))
    #- Simply grab the names
    names = []
    for i in range(3):
        names.append(inputhelp.getSelectedArrayName(self, i))
    # Pass array names and associations on to process
    # Get the input arrays
    wpdi = dsa.WrapDataObject(pdi)
    arrs = []
    for i in range(3):
        arrs.append(inputhelp.getArray(wpdi, fields[i], names[i]))

    # grab coordinates for each part of boring machine at time idx as row
    executive = self.GetExecutive()
    outInfo = executive.GetOutputInformation(0)
    idx = int(outInfo.Get(executive.UPDATE_TIME_STEP())/dt)
    x = arrs[0][idx]
    y = arrs[1][idx]
    z = arrs[2][idx]
    center = (x,y,z)
    pts = []
    nrows = int(self.GetInput().GetColumn(0).GetNumberOfTuples())

    # now compute unit vector.
    def unitVec(s, g):
        # Direction Vector: Vector points from receiver to source
        vec = (s[0]-g[0], s[1]-g[1], s[2]-g[2])
        print("vec", vec)
        # Total spatial distance:
        dist = np.sqrt(vec[0]**2 + vec[1]**2 + vec[2]**2)
        # Get unit vector for direction
        return (vec[0]/dist, vec[1]/dist, vec[2]/dist)

    if idx == (nrows - 1):
        # use vect between current and last different points
        iii = 1
        for i in range(1,idx):
            if arrs[0][idx-i] != x or arrs[1][idx-i] != y or arrs[2][idx-i] != z:
                iii = i
                break
        vec = unitVec((arrs[0][idx-iii],arrs[1][idx-iii],arrs[2][idx-iii]), center)
    else:
        # get vector from current point to next different point.
        iii = 1
        for i in range(1,nrows-idx):
            if arrs[0][idx+i] != x or arrs[1][idx+i] != y or arrs[2][idx+i] != z:
                iii = i
                break
        vec = unitVec(center, (arrs[0][idx+iii],arrs[1][idx+iii],arrs[2][idx+iii]))

    # Generate two more points Length/2 away in pos/neg unit vector direction
    def genPts(vec, c, l):
        """Generates two points l dist away from c in direction vec"""
        x1 = c[0] - (vec[0] * l)
        y1 = c[1] - (vec[1] * l)
        z1 = c[2] - (vec[2] * l)
        x2 = c[0] + (vec[0] * l)
        y2 = c[1] + (vec[1] * l)
        z2 = c[2] + (vec[2] * l)
        return ((x1,y1,z1), (x2,y2,z2))

    # append the points and done. 3 points total
    add = genPts(vec, center, Length/2)
    #- append neg first
    pts.append(add[0])
    #- append center
    pts.append(center)
    #- append pos last
    pts.append(add[1])

    # Generate tube:
    vtk_pts = vtk.vtkPoints()
    for i in range(len(pts)):
        vtk_pts.InsertNextPoint(pts[i][0],pts[i][1],pts[i][2])
    poly = vtk.vtkPolyData()
    poly.SetPoints(vtk_pts)
    pointsToTube(poly, radius=Diameter/2, numSides=20, nrNbr=False, pdo=pdo)


def RequestInformation(self):
    import numpy as np
    executive = self.GetExecutive()
    outInfo = executive.GetOutputInformation(0)
    # Calculate list of timesteps here
    #- Get number of rows in table and use that for num time steps
    nrows = int(self.GetInput().GetColumn(0).GetNumberOfTuples())
    xtime = np.arange(0,nrows*dt,dt, dtype=float)
    outInfo.Remove(executive.TIME_STEPS())
    for i in range(len(xtime)):
        outInfo.Append(executive.TIME_STEPS(), xtime[i])
    # Remove and set time range info
    outInfo.Remove(executive.TIME_RANGE())
    outInfo.Append(executive.TIME_RANGE(), xtime[0])
    outInfo.Append(executive.TIME_RANGE(), xtime[-1])
