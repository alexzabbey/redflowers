new Vue({
  el: "#file-drag-drop",
  data() {
    return {
      dragAndDropCapable: false,
      file: null,
      fileb: "none",
      filename: null,
      result: false,
      isActive: false,
      isPicShowing: false,
      isBad: false,
      isGood: false,
      clicked: false,
      allThree: {
        calanit: "כלנית",
        nurit: "נורית",
        pereg: "פרג"
      },
      feedback: null,
      otherTwo: [],
      width: null,
      height: null
    };
  },

  mounted() {
    this.dragAndDropCapable = this.determineDragAndDropCapable();
    if (this.dragAndDropCapable) {
      [
        "drag",
        "dragstart",
        "dragend",
        "dragover",
        "dragenter",
        "dragleave",
        "drop"
      ].forEach(evt => {
        this.$refs.fileform.addEventListener(
          evt,
          e => {
            e.preventDefault();
            e.stopPropagation();
          },
          false
        );
      });
      this.$refs.fileform.addEventListener("drop", e => {
        if (e.dataTransfer.files.length === 1) {
          this.file = e.dataTransfer.files[0];
          this.loadPhoto();
        } // TODO: what if more than 1?
      });
      this.$refs.fileform.addEventListener(
        "dragenter",
        () => (this.isActive = true)
      );
      this.$refs.fileform.addEventListener(
        "dragleave",
        () => (this.isActive = false)
      );
    }
  },
  methods: {
    isMobile() {
      if (
        /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
          navigator.userAgent
        )
      ) {
        return true;
      } else {
        return false;
      }
    },
    determineDragAndDropCapable() {
      var div = document.createElement("div");
      return (
        ("draggable" in div || ("ondragstart" in div && "ondrop" in div)) &&
        "FormData" in window &&
        "FileReader" in window
      );
    },
    translate(w) {
      for (let [key, value] of Object.entries(this.allThree)) {
        if (w === key) {
          return value;
        } else if (w === value) {
          return key;
        } else if (w === "נכון") {
          return true;
        }
      }
    },
    processFile(event) {
      this.file = event.target.files[0];
      this.loadPhoto();
    },
    loadPhoto() {
      // TODO: uploading the same photo should alert or just act normal
      if (/\.(jpe?g|png|gif)$/i.test(this.file.name)) {
        let reader = new FileReader();

        reader.addEventListener(
          "load",
          () => {
            this.fileb = "url(" + reader.result + ")";
            var img = new Image();
            img.src = reader.result;
            img.onload = () => {
              if (this.isMobile()) {
                let ratio = img.height / img.width;
                this.height =
                  ratio <= 1 ? (ratio * 100).toString() + "%" : "100%";
              } else {
                let ratio = img.width / img.height;
                this.width =
                  ratio >= 1 ? "100%" : (ratio * 100).toString() + "%";
              }
            };
          },
          false
        );
        reader.readAsDataURL(this.file);
        this.sendFeedback();
        this.clicked = false;
        this.result = false;
        this.otherTwo = [];
        this.isPicShowing = true;
      } else {
        console.log("not a pic!");
      }
    },
    submitFiles() {
      if (this.file) {
        this.clicked = true;
        let formData = new FormData();
        formData.append("file", this.file);
        axios
          .post("/analyze", formData)
          .then(response => {
            console.log(response);
            this.result = this.translate(response["data"]["prediction"]);
            this.otherTwo = ["נכון"].concat(
              Object.values(this.allThree).filter(value => {
                return value != this.result;
              })
            );
            this.filename = response["data"]["filename"];
          })
          .catch(error => {
            console.log(error);
            this.result = "שגיאה";
            this.isBad = true;
          });
      } else {
        console.log("no file selected!");
      }
    },
    sendFeedback(feedback) {
      console.log(feedback);
      if (feedback) {
        if (feedback === "נכון") {
          this.isGood = true;
          this.isBad = false;
          this.result = "מעולה! תודה על הפידבק";
        } else if (
          feedback === this.otherTwo[1] ||
          feedback === this.otherTwo[2]
        ) {
          this.isBad = true;
          this.isGood = false;
          this.result = "אוי לא! תודה על הפידבק";
        }
        axios
          .post("/feedback", {
            filename: this.filename,
            feedback: this.translate(feedback)
          })
          .then(response => console.log(response))
          .catch(error => console.log(error));
      } else {
        this.isBad = false;
        this.isGood = false;
        this.feedback = null;
      }
    },
    // onUploadProgress(progressEvent) {
    //   this.uploadPercentage = parseInt(
    //     Math.round((progressEvent.loaded * 100) / progressEvent.total)
    //   );
    // },
    removeFile() {
      //TODO: is necessary?
      this.file = null;
    }
  }
});
