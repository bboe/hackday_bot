"""hackday_bot.bot module."""
import json
import logging
import os
import re
import time

from prawcore.exceptions import NotFound, PrawcoreException

AVAILABLE_COMMANDS = {
    'help': 'Output this help message.',
    'interested': 'Indicate interest in the project.',
    'join': 'Indicate intent to join the project.',
    'leave': 'Leave the project.',
    'uninterested': 'Remove your interest in the project.'
}
COMMAND_RE = re.compile(r'(?:\A|\s)!({})(?=\s|\Z)'
                        .format('|'.join(AVAILABLE_COMMANDS)))
SEEN_COMMENT_PATH_TEMPLATE = os.path.join(os.environ['HOME'], '.config',
                                          'hackday_bot_comments_{}.json')


logger = logging.getLogger(__package__)


class Bot(object):
    """Bot manages comments made to the specified subreddit."""

    def __init__(self, subreddit):
        """Initialize an instance of Bot.

        :param subreddit: The subreddit to monitor for new comments.
        """
        self._seen_comment_path = SEEN_COMMENT_PATH_TEMPLATE.format(subreddit)
        self._seen_comments = self._load_seen_comments()
        self.members = Members(subreddit)
        self.subreddit = subreddit

    def _command_help(self, comment):
        table_rows = ['command|description',
                      ':---|:---']
        for command, description in sorted(AVAILABLE_COMMANDS.items()):
            table_rows.append('!{}|{}'.format(command, description))
        comment.reply('\n'.join(table_rows))

    def _command_interested(self, comment):
        comment.reply('soon I will record your interest')

    def _command_join(self, comment):
        message = self.members.add(comment)
        comment.reply(message)

    def _command_leave(self, comment):
        message = self.members.remove(comment)
        comment.reply(message)

    def _command_uninterested(self, comment):
        comment.reply('soon I will record your uninterest')

    def _handle_comment(self, comment):
        commands = set(COMMAND_RE.findall(comment.body))
        if len(commands) > 1:
            comment.reply('Please provide only a single command.')
        elif len(commands) == 1:
            command = commands.pop()
            getattr(self, '_command_{}'.format(command))(comment)
            logger.debug('Handled {} by {}'.format(command, comment.author))

    def _load_seen_comments(self):
        try:
            with open(self._seen_comment_path) as fp:
                data = set(json.load(fp))
            logger.debug('Discovered {} seen comments'.format(len(data)))
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            data = set()
        return data

    def _save_seen_comments(self):
        with open(self._seen_comment_path, 'w') as fp:
            json.dump(sorted(self._seen_comments), fp)
        logger.debug('Recorded {} seen comments'
                     .format(len(self._seen_comments)))

    def run(self):
        """Run the bot indefinitely."""
        running = True
        subreddit_url = '{}{}'.format(self.subreddit._reddit.config.reddit_url,
                                      self.subreddit.url)
        logger.info('Watching for comments on: {}'.format(subreddit_url))
        while running:
            try:
                for comment in self.subreddit.stream.comments():
                    if comment.id in self._seen_comments:
                        continue
                    self._handle_comment(comment)
                    self._seen_comments.add(comment.id)
            except KeyboardInterrupt:
                logger.info('Termination received. Goodbye!')
                running = False
            except PrawcoreException:
                logger.exception('run loop')
                time.sleep(10)
        self._save_seen_comments()
        return 0


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

        self._save_projects('test')

    def _comment_info(self, comment):
        assignees = self.projects.setdefault(
            comment.link_url, {'assignees': set(),
                               'title': comment.link_title}
        )['assignees']
        return assignees, str(comment.author)

    def _load_projects(self):
        projects = {}
        url = None
        for line in self._page.content_md.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                title, url = line[3:-1].split('](')
                projects[url] = {'assignees': set(), 'title': title}
            elif line.startswith('*'):
                username = line.rsplit('/', 1)[1]
                projects[url]['assignees'].add(username)
        logger.debug('Loaded {} project(s)'.format(len(projects)))
        return projects

    def _save_projects(self, reason):
        lines = []
        for url, data in sorted(self.projects.items(),
                                key=lambda x: x[1]['title']):
            if not data['assignees']:
                continue
            lines.append('# [{}]({})'.format(data['title'], url))
            for member in sorted(data['assignees']):
                lines.append('* /u/{}'.format(member))
        self._page.edit('\n'.join(lines), reason=reason)

    def add(self, comment):
        """Add user who made comment to project associated with the comment."""
        assignees, user = self._comment_info(comment)
        if user in assignees:
            return 'You have already joined this project.'
        assignees.add(user)
        self._save_projects('join {} to {}'.format(user, comment.link_id))
        return 'You have successfully joined the project.'

    def remove(self, comment):
        """Remove user who made comment from comment's project."""
        assignees, user = self._comment_info(comment)
        if user not in assignees:
            return 'You have not joined this project.'
        assignees.remove(user)
        self._save_projects('leave {} from {}'.format(user, comment.link_id))
        return 'You have been removed from the project.'
