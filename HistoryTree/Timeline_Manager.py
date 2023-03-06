import traceback
import adsk.fusion as fusion
import adsk.core as core
# import itertools
import json
from .lib.VerticalTimeline import get_feature_image, get_body_image

# ID重複を避ける為のカウンター
_idCount = 0

TEST = False
TEST_COUNT = 12

def run(context):
    ui = core.UserInterface.cast(None)
    try:
        app: core.Application = core.Application.get()
        ui = app.userInterface

        dict = getBodiesTree()

        print(json.dumps(dict, indent=2, ensure_ascii=False))
        app.log(f'{json.dumps(dict, indent=2, ensure_ascii=False)}')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def getBodiesTree() -> dict:
    '''
    履歴をDictで取得
    '''

    # Expansion
    fusion.ExtrudeFeature.getRefs = getReferences_Extrude
    fusion.RevolveFeature.getRefs = getReferences_Extrude
    fusion.LoftFeature.getRefs = getReferences_Loft
    fusion.SweepFeature.getRefs = getReferences_Sweep
    fusion.HoleFeature.getRefs = getReferences_Hole

    fusion.CombineFeature.getRefs = getReferences_Combine

    fusion.Feature.isBoolOpe = is_boolen_operation

    # ************
    def initBodyInfo(body: fusion.BRepBody) -> dict:
        return {
            'id' : body.entityToken,
            'text' : body.name,
            'icon' : get_body_image(body),
            'children' : [],
        }

    def initFeatureInfo(feat: fusion.Feature) -> dict:
        if hasattr(feat, 'getRefs'):
            children = feat.getRefs()
        else:
            children = []

        # global _idCount
        # _idCount += 1
        return {
            # 'id' : f'{feat.entityToken}@{_idCount}',
            'id' : feat.entityToken,
            'text' : feat.name,
            'icon' : get_feature_image(feat.timelineObject),
            'children' : children,
        }

    # ******
    app: core.Application = core.Application.get()
    des: fusion.Design = app.activeProduct

    timeline: fusion.Timeline = des.timeline
    backupMarker = timeline.markerPosition

    bodiesDict = {}
    # sketchDict = {}

    timeObjs = [timeline.item(idx) for idx in range(timeline.count)]

    if TEST:
        timeObjs = timeObjs[:TEST_COUNT]

    for timeObj in timeObjs:
        timeObj: fusion.TimelineObject

        feat: fusion.Feature = fusion.Feature.cast(timeObj.entity)
        if not feat:
            continue

        timeObj.rollTo(False)
        afterBodies = get_all_bodies()

        if not hasattr(feat, 'bodies'):
            continue

        bodyInfos = [initBodyInfo(b) for b in feat.bodies]
        [bodiesDict.setdefault(info['id'], info) for info in bodyInfos]

        timeObj.rollTo(True)
        if feat.classType() == fusion.CombineFeature.classType():
            # 結合
            for info in bodyInfos:
                children = []
                featInfo = initFeatureInfo(feat)
                for token in featInfo['children']:
                    children.append(bodiesDict[token])
                    bodiesDict.pop(token)
                featInfo['children'] = children
                bodiesDict[info['id']]['children'].append(featInfo)

        # if feat.linkedFeatures.count > 0:
        #     a=1
        # if feat.classType() == fusion.RibFeature.classType():
        #     a=1

        else:
            # その他
            featInfo = initFeatureInfo(feat)

            # オペレーションで結合等を使った場合
            if feat.isBoolOpe():
                removeBodies = diff_list_by_entity(get_all_bodies(), afterBodies)

                for body in removeBodies:
                    token = body.entityToken
                    featInfo['children'].append(bodiesDict[token])
                    bodiesDict.pop(token) 

            # オペレーションでボディが分割された場合の表示が不完全
            [bodiesDict[info['id']]['children'].append(featInfo) for info in bodyInfos]

    timeline.markerPosition = backupMarker

    return bodiesDict


def initSketchInfo(skt: fusion.Sketch) -> dict:
    global _idCount
    _idCount += 1
    return {
        'id' : f'{skt.entityToken}@{_idCount}',
        'text' : skt.name,
        'icon' : get_feature_image(skt.timelineObject),
        'children' : [],
    }


# 全てのボディ取得
def get_all_bodies() -> list:
    '''
    全てのボディ取得
    '''
    app: core.Application = core.Application.get()
    des: fusion.Design = app.activeProduct

    comp: fusion.Component = None
    bodyLst = []
    for comp in des.allComponents:
        bodyLst.extend([b for b in comp.bRepBodies])
        bodyLst.extend([m for m in comp.meshBodies])

    return bodyLst


# オペレーションがNewでは無いタイプ
def is_boolen_operation(
    self: fusion.Feature
) -> bool:
    '''
    ボディの増減を確認
    '''

    if not hasattr(self, 'operation'):
        return False

    boolenTypes = [
        fusion.FeatureOperations.JoinFeatureOperation,
        fusion.FeatureOperations.CutFeatureOperation,
        fusion.FeatureOperations.IntersectFeatureOperation,
    ]

    return self.operation in boolenTypes


# 'adsk::fusion::RevolveFeature'
# 'adsk::fusion::ExtrudeFeature'
def getReferences_Extrude(self):
    '''
    押し出し・回転用
    '''

    def getParentEntity(prof):
        if hasattr(prof, 'parentSketch'):
            # return prof.parentSketch.name
            return initSketchInfo(prof.parentSketch)
        else:
            return

    parent = None
    try:
        prof = self.profile
        if hasattr(prof, '__iter__'):
            profs = [getParentEntity(p) for p in self.profile]
            parent = list(set(profs))
        else:
            parent = [getParentEntity(prof)]
    except:
        parent = []

    return get_unique_list(parent)

# 'adsk::fusion::LoftFeature'
def getReferences_Loft(self) -> list:
    '''
    ロフト用
    '''

    def getAllReference() -> list:
        refs = []

        for groupName in ['loftSections', 'centerLineOrRails']:
            try:
                group = getattr(self, groupName)
                refs.extend(e for e in group)
            except:
                continue

        return refs

    def getParent(sect) -> str:
        try:
            # return sect.entity.parentSketch.name
            return initSketchInfo(sect.entity.parentSketch)
        except:
            return None

    parent = None
    try:
        sections = getAllReference()
        sparent = removeBlanks([getParent(s) for s in sections])
    except:
        parent = []

    return get_unique_list(parent)


# 'adsk::fusion::SweepFeature'
def getReferences_Sweep(self) -> list:
    '''
    スイープ用
    '''

    def getParent(ent) -> str:
        try:
            # return ent.parentSketch.name
            return initSketchInfo(ent.parentSketch)
        except:
            return None

    parent = []
    # profile
    try:
        prof = self.profile
        if hasattr(prof, '__iter__'):
            profs = [getParent(p) for p in self.profile]
            parent = list(set(profs))
        else:
            parent = [getParent(prof)]
    except:
        pass

    #     parent.append(getParent(self.profile))
    # except:
    #     pass

    # path
    try:
        prof = self.profile
        if hasattr(prof, '__iter__'):
            profs = [getParent(p) for p in self.profile]
            parent.extend(list(set(profs)))
        else:
            parent.extend([getParent(prof)])
    except:
        pass


    #     parent.extend([getParent(p.entity) for p in self.path])
    # except:
    #     pass

    return get_unique_list(parent)


# 'adsk::fusion::HoleFeature'
def getReferences_Hole(self) -> list:
    '''
    穴用
    '''

    # def getParent(ent) -> str:
    #     try:
    #         # return ent.parentSketch.name
    #         return initSketchInfo(ent.parentSketch)
    #     except:
    #         return None
    def getParenSketch(ent) -> str:
        try:
            # return ent.parentSketch.name
            return ent.parentSketch
        except:
            return None

    parent = []
    try:
        points: core.ObjectCollection = self.holePositionDefinition.sketchPoints
        skts = get_unique_list([getParenSketch(p) for p in points])
        parent.extend([initSketchInfo(skt) for skt in skts])
        # parent.extend([getParent(p) for p in points])
    except:
        pass

    return parent


# 'adsk::fusion::CombineFeature'
def getReferences_Combine(self) -> list:
    '''
    結合用
    '''
    parent = []
    for body in self.toolBodies:
        parent.append(body.entityToken)

    return parent


def removeBlanks(lst: list):
    return list(filter(lambda x: x is not None, lst))


def diff_list_by_entity(lst1: list, lst2: list) -> list:
    return [e for e in lst1 if not e in lst2]

def get_unique_list(lst: list) -> list:
    uniqueLst = []
    [uniqueLst.append(x) for x in lst if not x in uniqueLst]

    return uniqueLst