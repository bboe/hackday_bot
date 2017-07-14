"""hackday_bot.members module."""
import logging

from prawcore.exceptions import NotFound


logger = logging.getLogger(__package__)


class Members(object):
    """Keeps track of members of the various projects."""

    def __init__(self, subreddit):
        """Initialize and instance of Members.

        :param subreddit: The subreddit for which projects are to be managed.

        """
        self._page = self._page = subreddit.wiki['projects']
        try:
            self.projects = self._load_projects()
        except NotFound:
            self._page = subreddit.wiki.create('projects', '')
            self.projects = {}
        self.wiki_link = '/' + self._page._info_path()

    def _comment_info(self, comment):
        data = self.projects.setdefault(
            comment.link_url, {'assignees': set(), 'interested': set(),
                               'title': comment.link_title}
        )
        return data['assignees'], data['interested'], str(comment.author)

    def _load_projects(self):
        projects = {}
        url = None
        for line in self._page.content_md.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                title, url = line[5:-1].split('](')
                projects[url] = {'assignees': set(), 'interested': set(),
                                 'title': title}
            elif line.startswith('* [INTERESTED]'):
                username = line.rsplit('/', 1)[1]
                projects[url]['interested'].add(username)
            elif line.startswith('*'):
                username = line.rsplit('/', 1)[1]
                projects[url]['assignees'].add(username)
        logger.debug('Loaded {} project(s)'.format(len(projects)))
        return projects

    def _save_projects(self, reason):
        lines = []
        for url, data in sorted(self.projects.items(),
                                key=lambda x: x[1]['title']):
            if not (data['assignees'] or data['interested']):
                continue
            lines.append('### [{}]({})'.format(data['title'], url))
            for member in sorted(data['assignees']):
                lines.append('* /u/{}'.format(member))
            for member in sorted(data['interested']):
                lines.append('* [INTERESTED] /u/{}'.format(member))
            lines.append('')
        self._page.edit('\n'.join(lines), reason=reason)

    def _update_flair(self, comment, assignees, interested):
        flair = []
        if assignees:
            flair.append('{} {}'.format(len(assignees), 'joined'))
        if interested:
            flair.append('{} {}'.format(len(interested), 'interested'))
        comment.submission.mod.flair('|'.join(flair))

    def add(self, comment):
        """Add user who made comment to project associated with the comment."""
        assignees, interested, user = self._comment_info(comment)
        if user in assignees:
            return 'You have already joined this project.'
        elif user in interested:
            interested.remove(user)
        assignees.add(user)
        self._save_projects('{} joined {}'.format(user, comment.link_id))
        self._update_flair(comment, assignees, interested)
        return 'You have successfully joined this project.'

    def add_interest(self, comment):
        """Indicte user is interested in comment's project."""
        assignees, interested, user = self._comment_info(comment)
        if user in interested:
            return 'You have already expressed interest in this project.'
        elif user in assignees:
            assignees.remove(user)
        interested.add(user)
        self._save_projects('{} interested in {}'
                            .format(user, comment.link_id))
        self._update_flair(comment, assignees, interested)
        return 'You have successfully expressed interest in this project.'

    def remove(self, comment):
        """Remove user who made comment from comment's project."""
        assignees, interested, user = self._comment_info(comment)
        if user in assignees:
            assignees.remove(user)
        elif user in interested:
            interested.remove(user)
        else:
            return 'You are not associated with this project.'
        self._save_projects('{} left {}'.format(user, comment.link_id))
        self._update_flair(comment, assignees, interested)
        return 'You have been removed from this project.'
