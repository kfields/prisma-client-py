from typing import Optional, List
from contextvars import ContextVar

import pytest

from prisma import Client
from prisma.models import Post


posts_ctx: ContextVar[Optional[List[Post]]] = ContextVar('posts_ctx', default=None)


@pytest.fixture(scope='module', name='user_id')
async def user_id_fixture(client: Client) -> str:
    user = await client.user.create({'name': 'Robert'})
    posts = await create_posts(client, user.id)
    await client.category.create(
        {
            'name': 'My Category',
            'posts': {'connect': [{'id': posts[0].id}, {'id': posts[1].id}]},
        }
    )
    return user.id


@pytest.fixture(scope='module', name='posts')
async def posts_fixture(client: Client, user_id: str) -> List[Post]:
    return await create_posts(client, user_id)


async def create_posts(client: Client, user_id: str) -> List[Post]:
    posts = posts_ctx.get()
    if posts is not None:
        return posts

    posts = [
        await client.post.create(
            {
                'title': 'Post 1',
                'published': False,
                'author': {'connect': {'id': user_id}},
            }
        ),
        await client.post.create(
            {
                'title': 'Post 2',
                'published': True,
                'author': {'connect': {'id': user_id}},
            }
        ),
        await client.post.create(
            {
                'title': 'Post 3',
                'published': True,
                'author': {'connect': {'id': user_id}},
            }
        ),
        await client.post.create(
            {
                'title': 'Post 4',
                'published': False,
                'author': {'connect': {'id': user_id}},
            }
        ),
    ]
    posts_ctx.set(posts)
    return posts


@pytest.mark.asyncio
async def test_find_unique_include(client: Client, user_id: str) -> None:
    user = await client.user.find_unique(where={'id': user_id}, include={'posts': True})
    assert user is not None
    assert user.name == 'Robert'
    assert len(user.posts) == 4

    for i, post in enumerate(user.posts, start=1):
        assert post.author is None
        assert post.author_id == user.id
        assert post.title == f'Post {i}'


@pytest.mark.asyncio
async def test_find_unique_include_take(client: Client, user_id: str) -> None:
    user = await client.user.find_unique(
        where={'id': user_id}, include={'posts': {'take': 1}}
    )
    assert user is not None
    assert len(user.posts) == 1


@pytest.mark.asyncio
async def test_find_unique_include_where(
    client: Client, user_id: str, posts: List[Post]
) -> None:
    user = await client.user.find_unique(
        where={'id': user_id},
        include={'posts': {'where': {'created_at': posts[0].created_at}}},
    )
    assert user is not None
    assert len(user.posts) == 1
    assert user.posts[0].id == posts[0].id


@pytest.mark.asyncio
async def test_find_unique_include_pagination(
    client: Client, user_id: str, posts: List[Post]
) -> None:
    user = await client.user.find_unique(
        where={'id': user_id},
        include={'posts': {'cursor': {'id': posts[0].id}, 'take': 1, 'skip': 1}},
    )
    assert user is not None
    assert len(user.posts) == 1
    assert user.posts[0].id == posts[1].id

    user = await client.user.find_unique(
        where={'id': user_id},
        include={'posts': {'cursor': {'id': posts[1].id}, 'take': -1, 'skip': 1}},
    )
    assert user is not None
    assert len(user.posts) == 1
    assert user.posts[0].id == posts[0].id


@pytest.mark.asyncio
async def test_create_include(client: Client) -> None:
    post = await client.post.create(
        {
            'title': 'Post 4',
            'published': False,
            'author': {'create': {'name': 'Bob'}},
        },
        include={'author': True},
    )
    assert post.author is not None
    assert post.author.name == 'Bob'