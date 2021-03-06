from .helper import timestamp_to_datetime
import six


class SlotPickleMixin(object):
    def __getstate__(self):
        if not self.__slots__:
            raise Exception('`__slots__` is required')
        return dict(
            (slot, getattr(self, slot))
            for slot in self.__slots__
            if hasattr(self, slot)
        )

    def __setstate__(self, state):
        for slot, value in state.items():
            setattr(self, slot, value)


class ApiModel(SlotPickleMixin):

    @classmethod
    def object_from_dictionary(cls, entry):
        # make dict keys all strings
        if entry is None:
            return ""
        entry_str_dict = dict([(str(key), value) for key, value in entry.items()])
        return cls(**entry_str_dict)

    def __repr__(self):
        return str(self)
        # if six.PY2:
        #     return six.text_type(self).encode('utf8')
        # else:
        #     return self.encode('utf8')

    def __str__(self):
        if six.PY3:
            return self.__unicode__()
        else:
            return unicode(self).encode('utf-8')


class Image(ApiModel):
    __slots__ = ('url', 'height', 'width')

    def __init__(self, url, width, height, **kwargs):
        self.url = url
        self.height = height
        self.width = width

    def __unicode__(self):
        return "Image: %s" % self.url


class Video(Image):

    def __unicode__(self):
        return "Video: %s" % self.url


class Media(ApiModel):
    __slots__ = (
        'id', 'type', 'user', 'images', 'videos', 'user_has_liked', 'like_count', 'likes', 'comment_count',
        'comments', 'users_in_photo', 'created_time', 'location', 'caption', 'tags', 'link', 'filter'
    )

    def __init__(self, id=None, **kwargs):
        self.id = id
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    def get_standard_resolution_url(self):
        if self.type == 'image':
            return self.images['standard_resolution'].url
        else:
            return self.videos['standard_resolution'].url

    def get_low_resolution_url(self):
        if self.type == 'image':
            return self.images['low_resolution'].url
        else:
            return self.videos['low_resolution'].url

    def get_thumbnail_url(self):
        return self.images['thumbnail'].url

    def __unicode__(self):
        return "Media: %s" % self.id

    @classmethod
    def object_from_dictionary(cls, entry):
        new_media = Media(id=entry['id'])
        new_media.type = entry['type']

        user_object = entry['user']
        try:
            user_id = entry['id'].split('_')[1]
        except IndexError:
            user_id = None
        user_object.update({
            'id': user_id
        })
        new_media.user = User.object_from_dictionary(user_object)

        new_media.images = {}
        for version, version_info in six.iteritems(entry['images']):
            new_media.images[version] = Image.object_from_dictionary(version_info)

        if '/null.jpg' in new_media.images['thumbnail'].url:
            new_media.type = 'carousel'

        if new_media.type == 'video' and 'videos' not in entry:
            new_media.type = 'carousel'

        if new_media.type == 'video':
            new_media.videos = {}
            for version, version_info in six.iteritems(entry['videos']):
                new_media.videos[version] = Video.object_from_dictionary(version_info)

        if 'user_has_liked' in entry:
            new_media.user_has_liked = entry['user_has_liked']
        new_media.like_count = entry['likes']['count']
        new_media.likes = []
        if 'data' in entry['likes']:
            for like in entry['likes']['data']:
                new_media.likes.append(User.object_from_dictionary(like))

        new_media.comment_count = entry['comments']['count']
        new_media.comments = []
        if 'data' in entry['comments']:
            for comment in entry['comments']['data']:
                new_media.comments.append(Comment.object_from_dictionary(comment))

        new_media.users_in_photo = []
        if entry.get('users_in_photo'):
            for user_in_photo in entry['users_in_photo']:
                new_media.users_in_photo.append(UserInPhoto.object_from_dictionary(user_in_photo))

        new_media.created_time = timestamp_to_datetime(entry['created_time'])

        if entry['location'] and 'id' in entry:
            new_media.location = Location.object_from_dictionary(entry['location'])

        new_media.caption = None
        if entry['caption']:
            caption_object = entry['caption']
            caption_object['from'] = user_object
            new_media.caption = Comment.object_from_dictionary(caption_object)

        new_media.tags = []
        if entry['tags']:
            for tag in entry['tags']:
                new_media.tags.append(Tag.object_from_dictionary({'name': tag}))

        new_media.link = entry['link']

        new_media.filter = entry.get('filter')

        return new_media


class MediaShortcode(Media):
    __slots__ = ('shortcode')

    def __init__(self, shortcode=None, **kwargs):
        self.shortcode = shortcode
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)


class Tag(ApiModel):
    __slots__ = ('media_count', 'name')

    def __init__(self, name, **kwargs):
        self.name = name
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    def __unicode__(self):
        return "Tag: %s" % self.name


class Comment(ApiModel):
    __slots__ = ('created_at', 'id', 'text', 'user')

    def __init__(self, *args, **kwargs):
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    @classmethod
    def object_from_dictionary(cls, entry):
        user = User.object_from_dictionary(entry['from'])
        text = entry['text']
        created_at = timestamp_to_datetime(entry['created_time'])
        id = entry['id']
        return Comment(id=id, user=user, text=text, created_at=created_at)

    def __unicode__(self):
        return "Comment: %s said \"%s\"" % (self.user.username, self.text)


class Point(ApiModel):
    __slots__ = ('latitude', 'longitude')

    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

    def __unicode__(self):
        return "Point: (%s, %s)" % (self.latitude, self.longitude)


class Location(ApiModel):
    __slots__ = ('id', 'point', 'name')

    def __init__(self, id, *args, **kwargs):
        self.id = str(id)
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    @classmethod
    def object_from_dictionary(cls, entry):
        point = None
        if 'latitude' in entry:
            point = Point(entry.get('latitude'),
                          entry.get('longitude'))
        location = Location(entry.get('id', 0),
                       point=point,
                       name=entry.get('name', ''))
        return location

    def __unicode__(self):
        return "Location: %s (%s)" % (self.id, self.point)


class User(ApiModel):
    __slots__ = ('bio', 'id', 'counts', 'full_name', 'is_business', 'profile_picture', 'username', 'website')

    def __init__(self, id, *args, **kwargs):
        self.id = id
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    def __unicode__(self):
        return "User: %s" % self.username


class Relationship(ApiModel):
    __slots__ = ('incoming_status', 'outgoing_status', 'target_user_is_private')

    def __init__(self, incoming_status="none", outgoing_status="none", target_user_is_private=False):
        self.incoming_status = incoming_status
        self.outgoing_status = outgoing_status
        self.target_user_is_private = target_user_is_private

    def __unicode__(self):
        follows = False if self.outgoing_status == 'none' else True
        followed = False if self.incoming_status == 'none' else True

        return "Relationship: (Follows: %s, Followed by: %s)" % (follows, followed)


class Position(ApiModel):
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __unicode__(self):
        return "Position: (%s, %s)" % (self.x, self.y)

    @classmethod
    def object_from_dictionary(cls, entry):
        if 'x' in entry:
            return Position(entry['x'], entry['y'])


class UserInPhoto(ApiModel):
    __slots__ = ('position', 'user')

    def __init__(self, user, position):
        self.position = position
        self.user = user

    def __unicode__(self):
        return "UserInPhoto: (%s, %s)" % (self.user, self.position)

    @classmethod
    def object_from_dictionary(cls, entry):
        user = None
        if 'user' in entry:
            user_object = entry['user']
            user_object['id'] = None
            user = User.object_from_dictionary(user_object)

        if 'position' in entry:
            position = Position(entry['position']['x'], entry['position']['y'])

        return UserInPhoto(user, position)
