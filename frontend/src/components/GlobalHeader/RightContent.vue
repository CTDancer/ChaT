<template>
  <div :class="wrpCls">
    <div class="search-avatar-wrapper">
      <div class="search">
        <input type="text" v-model="placeholder" @keydown.enter="onEnter" placeholder="Search" />
        <a-icon type="search"></a-icon>
      </div>
      <avatar-dropdown :menu="showMenu" :current-user="currentUser" :class="prefixCls" />
      <select-lang :class="prefixCls" />
    </div>
  </div>
</template>

<script>
import AvatarDropdown from './AvatarDropdown'
import SelectLang from '@/components/SelectLang'
// import { ref } from 'vue'

export default {
  name: 'RightContent',
  components: {
    AvatarDropdown,
    SelectLang
  },
  props: {
    prefixCls: {
      type: String,
      default: 'ant-pro-global-header-index-action'
    },
    isMobile: {
      type: Boolean,
      default: () => false
    },
    topMenu: {
      type: Boolean,
      required: true
    },
    theme: {
      type: String,
      required: true
    }
  },
  data () {
    return {
      placeholder: '', // 存储搜索框的文本内容
      showMenu: true,
      currentUser: {}
    }
  },
  computed: {
    wrpCls () {
      return {
        'ant-pro-global-header-index-right': true,
        [`ant-pro-global-header-index-${(this.isMobile || !this.topMenu) ? 'light' : this.theme}`]: true
      }
    }
  },
  mounted () {
    setTimeout(() => {
      this.currentUser = {
        name: 'Serati Ma'
      }
    }, 1500)
  },
  methods: {
    onEnter () {
      if (this.placeholder.trim() !== '') {
        console.log(this.placeholder)
        this.$router.push({ path: `/schoollife/workplace/search/${this.placeholder}` }).catch(() => {})
      }
    }
    // expandMenu () {
    //   this.showMenu = false // 隐藏顶部菜单
    // },
    // collapseMenu () {
    //   this.showMenu = true // 显示顶部菜单
    // }
  }
}
</script>

<style lang="less">

.search-avatar-wrapper {
  display: flex;
  align-items: center;
  gap: 10px; /* 设置搜索框和头像之间的间距 */
}

.search {
  display: flex;
  height: 30px;
  align-items: center;
  background-color: #f2f2f2;
  border-radius: 4px;
  padding: 6px;
}

.search input[type="text"] {
  border: none;
  background-color: transparent;
  outline: none;
  width: 100%;
}

</style>
