class Relation:
    prev = 'PREV'   # 前作
    next = 'NEXT'   # 续作
    unofficial = 'UNOFFICIAL'   # 番外
    official = 'OFFICIAL'       # 正片
    external = 'EXTERNAL'   # 外传
    true = 'TRUE'           # 正传
    series = 'SERIES'       # 同系列
    none = None
    deleted = 'DELETED'     # 关系图中，标记删除的直接关系。其他关系都不能覆盖该关系
    self = 'O'


RELATIONS = [Relation.prev, Relation.next, Relation.unofficial, Relation.official,
             Relation.external, Relation.true, Relation.series]


REVERSE_RELATION = {
    Relation.self: Relation.self,
    Relation.prev: Relation.next,
    Relation.next: Relation.prev,
    Relation.unofficial: Relation.official,
    Relation.official: Relation.unofficial,
    Relation.external: Relation.true,
    Relation.true: Relation.external,
    Relation.series: Relation.series,
    Relation.none: Relation.none,
    Relation.deleted: Relation.deleted
}


RELATION_LEVEL = {
    Relation.self: 6,
    Relation.deleted: 5,
    Relation.prev: 4,
    Relation.next: 4,
    Relation.unofficial: 3,
    Relation.official: 3,
    Relation.external: 2,
    Relation.true: 2,
    Relation.series: 1,
    None: 0
}


def reverse_relation(relation):
    if relation is not None and relation[:1] == '#':
        return '#' + REVERSE_RELATION[relation[1:]]
    else:
        return REVERSE_RELATION[relation]


def relation_level(relation):
    if relation is None:
        return 0
    elif relation[:1] == '#':
        return 6
    else:
        return RELATION_LEVEL[relation]


def relation_calc(a, b):
    if a == b:
        return a
    elif a == Relation.series or b == Relation.series or relation_level(a) == relation_level(b):
        return Relation.series
    elif a == Relation.external or b == Relation.external:
        return Relation.external
    elif a == Relation.true or b == Relation.true:
        return Relation.true
    elif a == Relation.prev or b == Relation.prev:
        return Relation.prev
    elif a == Relation.next or b == Relation.next:
        return Relation.next
    else:
        return None


class RelationsMap(object):
    """
    用于在关系图发生更新时，重新拓扑关系网络。
    变化属性是很重要的。
    """
    def __init__(self, query, this_id, relations):
        self.animations = []
        self.relations = []
        self.count = 0
        self.query = query
        self.initialize(this_id, relations)
        self.storage_relations(original=True)
        self.spread()
        self.storage_relations(original=False)
        self.save()

    def initialize(self, this_id, relations):
        """
        将初始的局部关系导入，构成一张没有冗余的双向图。
        :param this_id:
        :param relations:
        :return:
        """
        # 构建用于构建的数据结构
        unique_set = set()      # 存储唯一id的标记数据结构
        queue = list()          # 处理队列
        this = self.query(this_id)
        # 首先将this引入到存储内
        unique_set.add(this_id)
        self.__new_element(this)
        queue.append((0, this, RelationsMap.build_init_relations(this.original_relations, relations)))
        # 开始处理队列
        while len(queue) > 0:
            (this_index, this, relations) = queue.pop(0)
            for (rel, obj_list) in relations.items():
                for animation_obj in obj_list:
                    # FIXED
                    if isinstance(animation_obj, dict):
                        animation_id = animation_obj.get('id')
                    else:
                        animation_id = animation_obj
                    # FIXED END
                    if animation_id not in unique_set:
                        unique_set.add(animation_id)
                        animation = self.query(animation_id)
                        if animation is not None:
                            animation_index = self.__new_element(animation)
                            if len(animation.original_relations) > 0:
                                queue.append((animation_index, animation, animation.original_relations))
                            self.__put_relation(this_index, animation_index, rel)
                    else:
                        animation_index = self.__find_element(animation_id)
                        self.__put_relation(this_index, animation_index, rel)
        for scale in self.relations:
            for i in range(0, len(scale)):
                if scale[i] == Relation.deleted:
                    scale[i] = Relation.none
                elif scale[i] is not None and scale[i][:1] == '#':
                    scale[i] = scale[i][1:]
        for i in range(0, self.count):
            self.relations[i][i] = Relation.self

    def spread(self):
        """
        从无冗余状态开始，推断出所有的冗余关系，使单一单元能获知所有联通单元的信息。
        :return:
        """
        for i in range(0, self.count):
            self.spread_one(i)

    def spread_one(self, this_index):
        """
        推断一个单元的联通单元。
        :param this_index:
        :return:
        """
        queue = list()
        unique_set = set()
        queue.append(this_index)
        unique_set.add(this_index)
        while len(queue) > 0:
            animation_index = queue.pop(0)
            this_to_animation_relation = self.relations[this_index][animation_index]
            for new_index in range(0, self.count):
                relation = self.relations[animation_index][new_index]
                if relation is not None:
                    this_to_new_relation = relation_calc(this_to_animation_relation, relation) if this_index != animation_index else relation
                    if self.__put_relation(this_index, new_index, this_to_new_relation) or new_index not in unique_set:
                        queue.append(new_index)
                        unique_set.add(new_index)

    def storage_relations(self, original):
        for animation_index in range(0, self.count):
            animation = self.animations[animation_index]
            relations = {}
            for goal_index in range(0, self.count):
                relation = self.relations[animation_index][goal_index]
                if goal_index != animation_index and relation is not None:
                    if relation not in relations:
                        rel_list = []
                        relations[relation] = rel_list
                    else:
                        rel_list = relations[relation]
                    rel_list.append({
                        'id': self.animations[goal_index].id,
                        'title': self.animations[goal_index].title,
                        'cover': self.animations[goal_index].cover
                    })
            if original:
                animation.original_relations = relations
            else:
                animation.relations = relations

    def save(self):
        for animation in self.animations:
            animation.save()

    def print(self):
        print('RELATION MAP:')
        for i in range(0, self.count):
            s = '%s: ' % (self.animations[i].id,)
            for relation in self.relations[i]:
                flag = relation[0:1] if relation is not None else ' '
                s += '%s ' % (flag,)
            print(s)

    def __new_element(self, animation):
        self.animations.append(animation)
        self.count += 1
        for scale in self.relations:
            scale.append(Relation.none)
        self.relations.append([Relation.none for _ in range(0, self.count)])
        return self.count - 1

    def __find_element(self, animation_id):
        i = 0
        for obj in self.animations:
            if obj.id == animation_id:
                return i
            else:
                i += 1
        return None

    def __put_relation(self, index1, index2, relation):
        old_relation = self.relations[index1][index2]
        if relation_level(old_relation) < relation_level(relation):
            self.relations[index1][index2] = relation
            self.relations[index2][index1] = reverse_relation(relation)
            return True
        return False

    def __get_relation(self, index1, index2):
        return self.relations[index1][index2]

    @staticmethod
    def build_init_relations(old_relations, new_relations):
        """
        比对animation relation时的新旧relation。
        这会将删除掉的部分添加到deleted标记下。
        被变更relation的animation，将会被标记为一个极高的优先级，以防止旧内容的覆盖。
        :param old_relations:
        :param new_relations:
        :return:
        """
        all_id_set = set()
        ret = {}
        for (rel, id_list) in new_relations.items():
            ret['#' + rel] = [animation_id for animation_id in id_list]
            for animation_id in id_list:
                all_id_set.add(animation_id)
        deleted = []
        for (rel, obj_list) in old_relations.items():
            for animation_obj in obj_list:
                # TODO FIXED 向前兼容的部分代码。这些代码可以在正式版本前移除。
                if isinstance(animation_obj, dict):
                    animation_id = animation_obj.get('id')
                else:
                    animation_id = animation_obj
                # FIXED END
                if animation_id not in all_id_set:
                    deleted.append(animation_id)
        if len(deleted) > 0:
            ret[Relation.deleted] = deleted
        return ret


def spread_cache_field(instance_id, relations, query, field_name, value):
    id_list = []
    for (rel, obj_list) in relations.items():
        for animation_obj in obj_list:
            # FIXED
            if isinstance(animation_obj, dict):
                animation_id = animation_obj.get('id')
            else:
                animation_id = animation_obj
            # FIXED END
            id_list.append(animation_id)
    if len(id_list) > 0:
        animations = query(id_list)
        # 处理每一个查找到的animation，修改其relations中的有关自己的field_name。original_relations无需修改。
        for animation in animations:
            flag = False
            for (rel, obj_list) in animation.relations.items():
                for animation_obj in obj_list:
                    # FIXED
                    if isinstance(animation_obj, dict) and animation_obj.get('id', None) == instance_id:
                        animation_obj[field_name] = value
                        flag = True
                    # FIXED END
            if flag:
                animation.save()
