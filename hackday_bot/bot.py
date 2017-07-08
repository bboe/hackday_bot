"""hackday_bot.bot module."""
import logging
import time

from prawcore.exceptions import PrawcoreException


logger = logging.getLogger(__package__)


class Bot(object):
    """Bot manages comments made to the specified subreddit."""

    def __init__(self, subreddit):
        """Initialize an instance of Bot.

        :param subreddit: The subreddit to monitor for new comments.
        """
        self.subreddit = subreddit

    def _handle_comment(self, comment):
        logger.info(comment)

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
