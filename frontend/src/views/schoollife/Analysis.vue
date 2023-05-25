<template>
  <div>
    <page-header-wrapper>
      <div class="centered-input">
        <a-input v-model="message" placeholder="发送一个帖子" @pressEnter="addPost" class="custom-input" />
      </div>
    </page-header-wrapper>
    <a-card :bordered="false" class="scrollable-card">
      <a-list
        item-layout="vertical"
        :pagination="false"
        class="post-list"
      >
        <a-list-item v-for="item in posts" :key="item.id">
          <a-list-item-meta description="">
            <a-avatar slot="avatar" size="medium" shape="circle" :src="item.avatar" />
            <a slot="title">{{ item.nickname }}</a>
          </a-list-item-meta>
          <!-- 回复内容 -->
          <div class="post-content" :contenteditable="isEditable(item)" @keydown.enter.prevent="saveItem(item, $event)">
            <p ref="content" @click="placeCaretAtEnd($event.target)">{{ item.content }}</p>
          </div>
          <!-- 时间 -->
          <div class="center_align">
            <a slot="time">{{ item.time_created | formatDate }}</a>
          </div>
          <div class="right_align">
            <!-- 修改图标 -->
            <a v-if="checkPermissionEdit(item)" @click="toggleEditMode(item)">
              <a-icon class="item-icon" type="edit"></a-icon>
            </a>

            <!-- 删除图标 -->
            <a v-if="checkPermission(item)" @click="deleteItem(item)">
              <a-icon class="item-icon" type="delete"></a-icon>
            </a>
            <!-- 点赞按钮 -->
            <a @click="toggleLike(item)">
              <a-icon
                class="item-icon"
                :class="{ 'red': item.isRed1, 'Gray': !item.isRed1}"
                type="like"></a-icon>
            </a>
            <span>{{ item.likes.length }}</span>

            <!-- 收藏按钮 -->
            <a @click="toggleFavorite(item)">
              <a-icon
                class="item-icon"
                :class="{ 'red': item.isRed2, 'Gray': !item.isRed2}"
                type="heart"></a-icon>
            </a>
            <span>{{ item.favourites.length }}</span>
            <!-- 评论按钮 -->
            <a-icon
              class="item-icon Gray"
              type="message"
              @click="goToReplyPage(item)"></a-icon>
            <span>{{ item.reply }}</span>
          </div>
        </a-list-item>
        <div slot="footer" style="text-align: center; margin-top: 16px;">
          <a-button v-if="!allLoaded" @click="loadMore" :loading="loadingMore">加载更多</a-button>
        </div>
      </a-list>
    </a-card>
  </div>
</template>

<script>
import { PageHeaderWrapper } from '@ant-design-vue/pro-layout'
import { Input } from 'ant-design-vue'
import { axios } from '@/utils/request'

export default {
  name: 'Workplace',
  components: {
    PageHeaderWrapper,
    'a-input': Input
  },
  data () {
    return {
      id: 0,
      posts: [],
      message: '',
      loadingMore: false,
      loading: true,
      index: 0,
      allLoaded: false,
      currentname: localStorage.getItem('nickname'),
      editingItem: null
    }
  },
  async created () {
    await this.fetchPosts()
  },
  filters: {
    formatDate: function (timestamp) {
      var date = new Date(timestamp)
      var year = date.getFullYear()
      var month = ('0' + (date.getMonth() + 1)).slice(-2)
      var day = ('0' + date.getDate()).slice(-2)
      var hours = ('0' + date.getHours()).slice(-2)
      var minutes = ('0' + date.getMinutes()).slice(-2)
      var seconds = ('0' + date.getSeconds()).slice(-2)
      return year + '-' + month + '-' + day + ' ' + hours + ':' + minutes + ':' + seconds
    }
  },
  methods: {
    fetchPosts () {
      console.log('fetchPosts')
      this.loading = true
      axios.get('http://127.0.0.1:8000/api/hole', { params: { division_id: 1, index: this.index, currentname: localStorage.getItem('nickname') } })
        .then(res => {
          console.log('after push I get')
          this.posts = res['posts']
          this.allLoaded = res['allLoaded']
        })
        .catch(err => {
          console.log('err:', err)
        })
        .finally(() => {
          this.loading = false
          console.log('posts:', this.posts)
        })
    },
    addPost () {
      if (this.message.trim() !== '') {
        axios.post('http://127.0.0.1:8000/api/hole', {
          index: this.index,
          content: this.message,
          nickname: localStorage.getItem('nickname'),
          division_id: 1 })
          .then(res => {
            var newPost = {
              id: res.id,
              nickname: localStorage.getItem('nickname'),
              avatar: null,
              content: this.message,
              likes: [],
              favourites: [],
              time_created: Date.now(),
              isRed1: 0,
              isRed2: 0,
              reply: 0
            }
            newPost.avatar = res.avatar
            this.posts.unshift(newPost)
            this.message = ''
            this.allLoaded = res['allLoaded']
            console.log('allLoaded:', this.allLoaded)
          })
          .catch(err => {
            console.log('err:', err)
          })
      } else {
        this.$message.error('内容不能为空')
      }
    },
    checkPermissionEdit (item) {
      return item.nickname === localStorage.getItem('nickname')
    },
    checkPermission (item) {
      const permission1 = (item.nickname === localStorage.getItem('nickname'))
      if (permission1) {
        return true
      } else {
        axios.get('http://127.0.0.1:8000/api/users', { params: { nickname: localStorage.getItem('nickname') } })
          .then(res => {
            console.log('permission: ', res['permission'])
            localStorage.setItem('permission', res['permission'])
          })
          .catch(err => {
            console.log('err:', err)
          })
          if (localStorage.getItem('permission') === 'user') {
            return false
          } else {
            return true
          }
      }
    },
    isEditable (item) {
      return this.editingItem === item
    },
    toggleEditMode (item) {
      this.editingItem = item
    },
    saveItem (item, event) {
      event.preventDefault()
      var newcontent = event.target.textContent.trim()
      if (newcontent === '') newcontent = '该帖子已被作者删除'
      else newcontent = newcontent + '（该帖子已被作者编辑）'
      console.log('newcontent:', newcontent)
      axios.put('http://127.0.0.1:8000/api/hole', { id: item.id, content: newcontent })
      .then(res => {
        console.log('changed content')
        this.editingItem = null
      })
      .catch(err => {
        console.log('err:', err)
      })
    },
    placeCaretAtEnd (target) {
      if (typeof window.getSelection !== 'undefined' && typeof document.createRange !== 'undefined') {
        const range = document.createRange()
        range.selectNodeContents(target)
        range.collapse(false)
        const selection = window.getSelection()
        selection.removeAllRanges()
        selection.addRange(range)
      } else if (typeof document.body.createTextRange !== 'undefined') {
        const textRange = document.body.createTextRange()
        textRange.moveToElementText(target)
        textRange.collapse(false)
        textRange.select()
      }
    },
    deleteItem (item) {
      if (item.nickname === localStorage.getItem('nickname')) {
        item.content = '该帖子已被作者删除'
      } else {
        item.content = '由于该帖子违反社区公约，已被管理员删除'
      }
      axios.put('http://127.0.0.1:8000/api/hole', { id: item.id, content: item.content })
        .then(res => {
          console.log('changed content')
        })
        .catch(err => {
          console.log('err:', err)
        })
    },
    toggleLike (item) {
      item.isRed1 = !item.isRed1
      const currentname = localStorage.getItem('nickname')
      const index = item.likes.indexOf(currentname)
      if (index > -1) {
        // 当前点赞列表中有当前用户，取消点赞
        item.likes.splice(index, 1)
      } else {
        // 当前点赞列表中没有当前用户，点赞
        item.likes.push(currentname)
      }
      console.log('item.id:', item.id)
      axios.put('http://127.0.0.1:8000/api/hole', { id: item.id, likes: item.likes })
        .then(res => {
          console.log('pass')
        })
        .catch(err => {
          console.log('err:', err)
        })
    },
    toggleFavorite (item) {
      item.isRed2 = !item.isRed2
      const currentname = localStorage.getItem('nickname')
      const index = item.favourites.indexOf(currentname)
      if (index > -1) {
        // 当前收藏列表中有当前用户，取消收藏
        item.favourites.splice(index, 1)
      } else {
        // 当前收藏列表中没有当前用户，收藏
        item.favourites.push(currentname)
      }
      axios.put('http://127.0.0.1:8000/api/hole', { id: item.id, favourites: item.favourites })
        .then(res => {
          console.log('pass')
        })
        .catch(err => {
          console.log('err:', err)
        })
    },
    loadMore () {
      this.loadingMore = true
      this.index += 1
      axios.get('http://127.0.0.1:8000/api/hole', { params: { division_id: 1, index: this.index } })
        .then(res => {
          // console.log('res.data:', res.data)
          this.allLoaded = res['allLoaded']
          this.posts = this.posts.concat(res['posts'])
        })
        .catch(err => {
          console.log('err:', err)
        })
        .finally(() => {
          this.loadingMore = false
        })
    },
    goToReplyPage (item) {
      const postId = item.id
			this.$router.push({ path: `/schoollife/workplace/reply/${postId}` })
    }
  }
}
</script>

<style lang="less" scoped>
@import './Workplace.less';

.fixed-bottom-input {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  padding: 16px;
  background-color: #f0f0f0;
  box-shadow: 0 -1px 4px rgba(0, 0, 0, 0.1);
}

.centered-input {
  display: flex;
  justify-content: center;
}

.custom-input {
  position: fixed;
  bottom: 15px;
  left: 16%;
  width: 68%;
  padding: 25px;
  border: none;
  border-radius: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.project-list {
  .card-title {
    font-size: 0;

    a {
      color: rgba(0, 0, 0, 0.85);
      margin-left: 12px;
      line-height: 24px;
      height: 24px;
      display: inline-block;
      vertical-align: top;
      font-size: 14px;

      &:hover {
        color: #1890ff;
      }
    }
  }

  .card-description {
    color: rgba(0, 0, 0, 0.45);
    height: 44px;
    line-height: 22px;
    overflow: hidden;
  }

  .project-item {
    display: flex;
    margin-top: 8px;
    overflow: hidden;
    font-size: 12px;
    height: 20px;
    line-height: 20px;

    a {
      color: rgba(0, 0, 0, 0.45);
      display: inline-block;
      flex: 1 1 0;

      &:hover {
        color: #1890ff;
      }
    }

    .datetime {
      color: rgba(0, 0, 0, 0.25);
      flex: 0 0 auto;
      float: right;
    }
  }

  .ant-card-meta-description {
    color: rgba(0, 0, 0, 0.45);
    height: 44px;
    line-height: 22px;
    overflow: hidden;
  }
}

.data {
  display: flex;
  justify-content: center;
  align-items: center;
}

.post-content {
    font-size: 16px;
}

.right_align {
    display: flex;
    justify-content: flex-end;
}

.center_align {
    display: flex;
    justify-content: center;
    margin-bottom: -2%;
}

.item-icon {
      font-size: 15px;
      color: rgba(0, 0, 0, 0.2);
      margin-left: 8px;
      margin-right: 8px;
      // margin-left: 16px;
      // vertical-align: middle;
      // cursor: pointer;
      // transition: color 0.3s;

      &:hover {
        color: #1890ff;
      }
    }

.red {
  color: red;
}

.Gray {
  color: gray;
}

.card-container {
  height: 700px; /* 设置容器的固定高度 */
  overflow-y: auto; /* 添加垂直滚动条 */
}

.scrollable-card {
  height: 660px; /* 设置a-card的固定高度 */
  overflow-y: auto; /* 添加垂直滚动条 */
}

.item-group {
  padding: 20px 0 8px 24px;
  font-size: 0;

  a {
    color: rgba(0, 0, 0, 0.65);
    display: inline-block;
    font-size: 14px;
    margin-bottom: 13px;
    width: 25%;
  }
}

.members {
  a {
    display: block;
    margin: 12px 0;
    line-height: 24px;
    height: 24px;

    .member {
      font-size: 14px;
      color: rgba(0, 0, 0, 0.65);
      line-height: 24px;
      max-width: 100px;
      vertical-align: top;
      margin-left: 12px;
      transition: all 0.3s;
      display: inline-block;
    }

    &:hover {
      span {
        color: #1890ff;
      }
    }
  }
}

.mobile {
  .project-list {
    .project-card-grid {
      width: 100%;
    }
  }

  .more-info {
    border: 0;
    padding-top: 16px;
    margin: 16px 0 16px;
  }

  .headerContent .title .welcome-text {
    display: none;
  }
}
</style>
