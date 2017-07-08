"""hackday_bot.bot module."""
import logging
import re
import time

from prawcore.exceptions import PrawcoreException

AVAILABLE_COMMANDS = ('help', 'interested', 'join', 'leave', 'uninterested')
COMMAND_RE = re.compile(r'(?:\A|\s)!({})(?=\s|\Z)'
                        .format('|'.join(AVAILABLE_COMMANDS)))


logger = logging.getLogger(__package__)


class Bot(object):
    """Bot manages comments made to the specified subreddit."""

    def __init__(self, subreddit):
        """Initialize an instance of Bot.

        :param subreddit: The subreddit to monitor for new comments.
        """
        self.subreddit = subreddit

    def _command_help(self, comment):
        comment.reply('help text will go here')

    def _command_interested(self, comment):
        comment.reply('soon I will record your interest')

    def _command_join(self, comment):
        comment.reply('soon I will record your sign up')

    def _command_leave(self, comment):
        comment.reply('soon I will record your abdication')

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

    def run(self):
        """Run the bot indefinitely."""
        running = True
        subreddit_url = '{}{}'.format(self.subreddit._reddit.config.reddit_url,
                                      self.subreddit.url)
        logger.info('Watching for comments on: {}'.format(subreddit_url))
        while running:
            try:
                for comment in self.subreddit.stream.comments():
                    self._handle_comment(comment)
            except KeyboardInterrupt:
                logger.info('Termination received. Goodbye!')
                running = False
            except PrawcoreException:
                logger.exception('run loop')
                time.sleep(10)
        return 0
