"""hackday_bot command line tool.

Usage: hackday_bot [options] SITE SUBREDDIT

Where:
  SITE       is the site name to load the bot's configuration from.
  SUBREDDIT  is the name of the subreddit to monitor.

The bot must be a moderator with wiki permissions on the subreddit.

Options:
  -h --help                     Output this message.
  -D --debug                    Show debugging messages.
  --version                     Output hackday_bot's version string.

"""

from __future__ import print_function

from docopt import docopt
from prawcore.exceptions import PrawcoreException
from update_checker import update_check
import praw

from .bot import Bot
from .const import __version__
from .util import prepare_logger


def main():
    """Provide the entry point to the hackday_bot command."""
    args = docopt(__doc__, version='hackday_bot v{}'.format(__version__))
    logger = prepare_logger('DEBUG' if args['--debug'] else 'INFO')
    update_check(__package__, __version__)

    reddit = praw.Reddit(args['SITE'], check_for_updates=False,
                         user_agent='hackday_bot/{}'.format(__version__))
    subreddit = reddit.subreddit(args['SUBREDDIT'])
    try:
        subreddit.name
    except PrawcoreException:
        logger.error('Invalid subreddit: {}'.format(args['SUBREDDIT']))
        return 1
    return Bot(subreddit).run()
