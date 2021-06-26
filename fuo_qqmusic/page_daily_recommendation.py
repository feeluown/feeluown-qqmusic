from feeluown.utils import aio
from feeluown.gui.page_containers.table import Renderer


async def render(req, **kwargs):
    app = req.ctx['app']
    provider = app.library.get('qqmusic')
    user = provider._user

    app.ui.right_panel.set_body(app.ui.right_panel.table_container)
    renderer = DailyRecommendationRenderer(user)
    await app.ui.right_panel.table_container.set_renderer(renderer)


class DailyRecommendationRenderer(Renderer):
    def __init__(self, user):
        self._user = user

    async def render(self):
        self.meta_widget.title = '每日推荐'
        self.meta_widget.show()

        self.show_songs(await aio.run_fn(lambda: self._user.rec_songs))
