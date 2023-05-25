<template>
  <div class="page-header-index-wide page-header-wrapper-grid-content-main">
    <a-row :gutter="24">
      <a-col :md="24" :lg="7">
        <a-card :bordered="false">
          <div class="account-center-avatarHolder">
            <div class="avatar" @click="uploadAvatar()">
              <img :src="avatar">
              <input type="file" id="avatarInput" style="display: none" accept="image/*">
            </div>
            <!-- <div>
              <input type="file" ref="fileInput" @change="handleFileUpload">
            </div> -->
            <div class="username">{{ nickname }}</div>
            <!-- <div class="bio">海纳百川，有容乃大</div> -->
          </div>
          <div class="account-center-detail">
            <!-- <p>
              <i class="title"></i>交互专家
            </p> -->
            <p>
              <i class="group"></i>{{ bio }}
            </p>
            <p>
              <i class="address"></i>
              <span>中国</span>
              <span>上海市</span>
            </p>
          </div>
          <a-divider/>
        </a-card>
      </a-col>
      <a-col :md="24" :lg="17">
        <a-card
          style="width:100%"
          :bordered="false"
          :tabList="this.tabList"
          :activeTabKey="noTitleKey"
          @tabChange="key => handleTabChange(key, 'noTitleKey')"
        >
          <article-page v-if="noTitleKey === 'yourPosts'"></article-page>
          <app-page v-else-if="noTitleKey === 'yourFavourites'"></app-page>
          <project-page v-else-if="noTitleKey === 'Users'"></project-page>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script>
import { PageView, RouteView } from '@/layouts'
import { axios } from '@/utils/request'
import { AppPage, ArticlePage, ProjectPage } from './page'

// import { mapGetters } from 'vuex'

export default {
  components: {
    RouteView,
    PageView,
    AppPage,
    ArticlePage,
    ProjectPage
  },
  data () {
    return {
      nickname: localStorage.getItem('nickname'),
      avatar: '',
      bio: 'You can write your bio in Account Settings',
      tags: ['很有想法的', '专注设计', '辣~', '大长腿', '川妹子', '海纳百川'],

      tagInputVisible: false,
      tagInputValue: '',

      teams: [],
      teamSpinning: true,

      tabList: [],

      tabListNoTitle: [
        {
          key: 'yourPosts',
          tab: '您的帖子'
        },
        {
          key: 'yourFavourites',
          tab: '您的收藏'
        },
        {
          key: 'Users',
          tab: '所有用户'
        }
      ],
      noTitleKey: 'yourPosts'
    }
  },
  created () {
    this.fetchUserAvatar()
    this.filteredTabListNoTitle()
  },
  // computed: {
  //   ...mapGetters(['nickname', 'avatar'])
  // },
  mounted () {
    this.fetchUserAvatar()
    this.getTeams()
  },
  methods: {
    fetchUserAvatar () {
      console.log('localStorage.getItem(nickname):', localStorage.getItem('nickname'))
      axios.get('http://127.0.0.1:8000/api/users', { params: { nickname: localStorage.getItem('nickname') } })
      .then(response => {
          // 从后端获取avatar属性值，并赋给avatar变量
          this.avatar = response['data']['avatar']
          this.bio = response['data']['bio']
          // console.log(this.avatar)
          // console.log(this.bio)
        })
        .catch(error => {
          console.error('Error fetching user avatar', error)
        })
      },
    handleFileUpload (event) {
      const file = event.target.files[0]
      const reader = new FileReader()

      reader.onload = () => {
        this.avatar = reader.result // 将上传的图片数据赋值给avatar变量
      }

      reader.readAsDataURL(file) // 读取文件数据
    },
    uploadAvatar () {
      // 找到文件上传的 input 元素
      var input = document.getElementById('avatarInput')

      // 设置 input 元素的 onchange 事件处理函数
      input.onchange = (e) => {
        var file = e.target.files[0] // 获取上传的文件
        var reader = new FileReader() // 创建一个文件读取器

        // 设置文件读取器的 onload 事件处理函数
        reader.onload = () => {
          var avatarImg = document.querySelector('.avatar img') // 找到 avatar 区域中的 img 元素
          avatarImg.src = reader.result // 设置 img 元素的 src 属性为读取的文件结果
          this.avatar = reader.result // 将读取的文件结果保存在名为 avatar 的变量中
          this.setAvatar(reader.result)
          localStorage.setItem('avatar', reader.result)
        }
        // 读取上传的文件
        reader.readAsDataURL(file)
      }

      // 触发点击文件上传的操作
      input.click()
    },
    setAvatar (avatar) {
      // console.log(avatar)
      axios.put('http://127.0.0.1:8000/api/users', { nickname: this.nickname, avatar: avatar })
      .then(res => {
        console.log('res')
      })
      .catch(err => {
        console.log(err)
      })
    },
    checkPermission () {
      axios.get('http://127.0.0.1:8000/api/users', { params: { nickname: localStorage.getItem('nickname') } })
        .then(res => {
          console.log('permission: ', res['permission'])
          localStorage.setItem('permission', res['permission'])
        })
        .catch(err => {
          console.log('err:', err)
        })
        if (localStorage.getItem('permission') === 'admin') {
          return true
        } else {
          return false
        }
    },
    filteredTabListNoTitle () {
      if (this.checkPermission()) {
        this.tabList = this.tabListNoTitle
      } else {
        this.tabList = this.tabListNoTitle.filter(item => item.key !== 'Users')
      }
    },
    getTeams () {
      this.$http.get('/workplace/teams').then(res => {
        this.teams = res.result
        this.teamSpinning = false
      })
    },

    handleTabChange (key, type) {
      this[type] = key
    },

    handleTagClose (removeTag) {
      const tags = this.tags.filter(tag => tag !== removeTag)
      this.tags = tags
    },

    showTagInput () {
      this.tagInputVisible = true
      this.$nextTick(() => {
        this.$refs.tagInput.focus()
      })
    },

    handleInputChange (e) {
      this.tagInputValue = e.target.value
    },

    handleTagInputConfirm () {
      const inputValue = this.tagInputValue
      let tags = this.tags
      if (inputValue && !tags.includes(inputValue)) {
        tags = [...tags, inputValue]
      }

      Object.assign(this, {
        tags,
        tagInputVisible: false,
        tagInputValue: ''
      })
    }
  }
}
</script>

<style lang="less" scoped>
.page-header-wrapper-grid-content-main {
  width: 100%;
  height: 100%;
  min-height: 100%;
  transition: 0.3s;

  .account-center-avatarHolder {
    text-align: center;
    margin-bottom: 24px;

    & > .avatar {
      margin: 0 auto;
      width: 104px;
      height: 104px;
      margin-bottom: 20px;
      border-radius: 50%;
      overflow: hidden;
      img {
        height: 100%;
        width: 100%;
      }
      cursor: pointer;
    }

    .username {
      color: rgba(0, 0, 0, 0.85);
      font-size: 20px;
      line-height: 28px;
      font-weight: 500;
      margin-bottom: 4px;
    }
  }

  .account-center-detail {
    p {
      margin-bottom: 8px;
      padding-left: 26px;
      position: relative;
    }

    i {
      position: absolute;
      height: 14px;
      width: 14px;
      left: 0;
      top: 4px;
      background: url(https://gw.alipayobjects.com/zos/rmsportal/pBjWzVAHnOOtAUvZmZfy.svg);
    }

    .title {
      background-position: 0 0;
    }
    .group {
      background-position: 0 -22px;
    }
    .address {
      background-position: 0 -44px;
    }
  }

  .account-center-tags {
    .ant-tag {
      margin-bottom: 8px;
    }
  }

  .account-center-team {
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
  }

  .tagsTitle,
  .teamTitle {
    font-weight: 500;
    color: rgba(0, 0, 0, 0.85);
    margin-bottom: 12px;
  }
}
</style>
