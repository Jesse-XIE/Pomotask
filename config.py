class Config:
    # available notification types:
    #   - buble: uses bash command notify-send
    #   - popup: uses bash command zenity
    notif_type = 'buble'

    # the file where your task tree could be found
    task_file = './tasks.md'

    # text editor used to edit task tree, should be callable from command line
    editor = 'subl'    

    # tab size used in your task file
    file_tab_size = 4   

    # tab size used to render the task tree
    print_tab_size = 4

    # default time for the pomodoro timer, in minutes
    pomodoro_time = 25  
    short_break_time = 5
    long_break_time = 15



