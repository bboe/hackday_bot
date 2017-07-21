"""hackday_bot.bot module."""
import json
import logging
import os
import re
import time

from prawcore.exceptions import PrawcoreException

from .members import Members

AVAILABLE_COMMANDS = {
    'help': 'Output this help message.',
    'interested': ('Indicate interest in this project. If you previously '
                   'joined this project, your association is downgraded.'),
    'join': ('Indicate intent to work on this project. If you previously '
             'expressed interest in this project your association is '
             'upgraded.'),
    'leave': 'Remove any association you have with this project.'}
COMMAND_RE = re.compile(r'(?:\A|\s)`?!({})`?(?=\s|\Z)'
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
        return '\n'.join(table_rows)

    def _command_interested(self, comment):
        return self.members.add_interest(comment)

    def _command_join(self, comment):
        return self.members.add(comment)

    def _command_leave(self, comment):
        return self.members.remove(comment)

    def _handle_comment(self, comment):
        commands = set(COMMAND_RE.findall(comment.body))
        if len(commands) > 1:
            comment.reply(
                self._template('Please provide only a single command.'))
        elif len(commands) == 1:
            command = commands.pop()
            message = getattr(self, '_command_{}'.format(command))(comment)
            comment.reply(self._template(message))
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

    def _template(self, message):
        return '\n\n'.join([
            message, '[See All Projects with Members]({})'.format(
                self.members.wiki_link),
            '> [Hackday Bot](https://github.com/bboe/hackday_bot) by BBoe'])

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
